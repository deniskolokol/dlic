import os
from collections import defaultdict, Counter
import numpy as np
from . import gnumpy as g
from .. import get_logger
from .opt.utils import nonlin
from .opt.d.generic import Generic3dData
from .opt.m.rnn.mrnn import MRNN
from .util import (shmem_as_ndarray, to_gpu, mcpu,
                   to_masked_array_of_different_len as to_masked)


log = get_logger('WORKER')


class BaseWorker(object):

    def __init__(self, worker_id, gpu_id, settings):
        log.debug('WORKER %s process PID: %s' % (worker_id, os.getpid()))
        self.gpu_id = gpu_id
        self.worker_id = worker_id
        self.settings = settings

        log.name = 'WORKER %s' % worker_id
        # Initialization of gnumpy
        self.init_gpu()
        # RNG initialization
        SEED = 10
        SEED += worker_id ## ESSENTIAL
        log.info('SEED: %s' % SEED)
        g.seed_rand(SEED)
        np.random.seed(SEED + 1)

        self.dp = Generic3dData(
            T=settings.T, v=settings.v, o=settings.o,
            batch_size=settings.batch_size*len(settings.grad_batches)*3,
            out_nonlin=nonlin.get(settings.worker_params.get('out_nonlin')),
            data_sizes={
                'grad': len(settings.grad_batches),
                'gn': len(settings.GN_batches),
                'test': len(settings.test_batches),
                'line_search': len(settings.line_search_batches)
                },
            num_timesteps=settings.number_of_timesteps_to_use,
            dp_data = settings.worker_params['dp_data']
        )

        self.train_batches, self.test_batches, self.valid_batches = \
            self.dp.train_batches, self.dp.test_batches, self.dp.valid_batches
        v, o, h, f = settings.v, settings.o, settings.h, settings.f
        self.W = MRNN(v, h, f, o,
                 hid_nonlin = nonlin.Tanh,
                 out_nonlin = self.dp.out_nonlin,
                 number_of_timesteps_to_use=settings.number_of_timesteps_to_use)
        KK = settings.KK
        init_scale = 1./np.sqrt(KK)
        self.W.initialize_self(KK, init_scale)
        X = self.W.pack()
        print 'X size = ', X.size

        self.gauss_newton_state = None
        self.gauss_newton_old_bid = None

        self.init_damping = settings.init_damping

        self.init_X = X

        self.message = '\n'.join(['SEED = %s' % SEED,
                                  'KK = %s' % KK,
                                  'init_scale = %s' % init_scale])

    def init_gpu(self):
        print 'worker %s, gpu_id %s: about to import gnumpy.' % (self.worker_id,
                                                                 self.gpu_id)
        g.board_id_to_use = self.gpu_id
        g._init_gpu()
        g.max_memory_usage = self.settings.worker_params['dp_data']['memory']
        log.info("Gnumpy max_memory_usage=%s" % (g.max_memory_usage,))
        print 'worker %s, gpu_id %s: successfully imported gnumpy.' % (self.worker_id,
                                                                       self.gpu_id)

    def L2_loss(self, X, batch):
        batch_size = self.dp.size(batch)
        return (X*X).sum() * (batch_size * self.settings.L2_decay) * 0.5

    def L2_grad(self, X, batch):
        batch_size = self.dp.size(batch)
        return X * batch_size * self.settings.L2_decay

    def L2_curvature(self, X, batch):
        batch_size = self.dp.size(batch)
        return batch_size * self.settings.L2_decay

    def L2_R(self, X, R, batch):
        batch_size = self.dp.size(batch)
        return R * batch_size * self.settings.L2_decay

    def forward_pass(self, batch, X, mask):
        W_X = self.W.unpack(X)
        (V, A, B, H, OX) = W_X.forward_pass(batch, mask=mask)
        return (V, A, B, H, OX)

    def get_accuracy(self, batch, X):
        W_X = self.W.unpack(X)
        accuracy_for_each_ts, confusion, weights = W_X.get_accuracy(batch)
        return accuracy_for_each_ts, confusion, weights

    def losses(self, batch, X, mask):
        # X: garray
        W_X = self.W.unpack(X)
        # W_X: MRNN instance initialized with X
        ans = W_X.loss(batch, mask=mask)

        bpc = ans/np.log(2)/self.dp.true_T

        return np.array([ans + self.L2_loss(X, batch), ans, bpc])

    def grad_grad2_losses(self, batch, X, mask):

        W_X =  self.W.unpack(X)

        grad, grad2, loss = W_X.grad(batch, compute_grad2=True, mask=mask)

        grad2 = grad2.pack() + self.L2_curvature(X, batch)
        grad = grad.pack() + self.L2_grad(X, batch)
        ans = full_loss = loss + self.L2_loss(X, batch)

        bpc = ans/np.log(2)/self.dp.true_T

        losses = np.array([full_loss, loss, bpc])
        return (grad, grad2, losses)

    def gauss_newton(self, bid, batch=None, X=None, R=None,
                     damping_factor=None, mask=None):

        if bid == 'forget':
            self.gauss_newton_state = None
            return

        W_X = self.W.unpack(X)
        W_R = self.W.unpack(R)

        # state caching:
        if (bid != self.gauss_newton_old_bid) or (self.gauss_newton_state is None):
            I = batch[0]
            O = batch[1]
            self.gauss_newton_state = W_X.forward_pass((I,O),mask=mask)
            self.gauss_newton_old_bid = bid

        mu = float(damping_factor[1])
        ans = W_X.gauss_newton(batch, W_R, state=self.gauss_newton_state, mu=mu).pack()

        return ans + self.L2_R(X,R, batch)


class Worker(BaseWorker):
    def __init__(self, worker_id, gpu_id, settings, command_pipe, ans_pipe,
                 X_size, X_shared, R_shared, GN_shared, total_batches,
                 total_batches_lock):
        # most essentially, the first time gnumpy is imported must be here,
        # on the new process.
        print 'calling _init_gpu: initializing the GPU.'

        super(Worker, self).__init__(worker_id, gpu_id, settings)

        self.ans_pipe = ans_pipe
        self.command_pipe = command_pipe
        self.total_batches = total_batches
        self.total_batches_lock = total_batches_lock
        # convert the shared mem vars into usable numpy arrays
        self.np_X, self.np_R, self.np_MY_ANS = \
                [shmem_as_ndarray(x)[:X_size]
                 for x in (X_shared, R_shared, GN_shared[worker_id])]

        # this little variable is used to speedup gauss_newton --- see below.
        self.gauss_newton_order = True

        print 'worker %s: successfully accessed shared vars and is can now function.' % gpu_id

    def run(self):
        while True:
            # receive the command
            cmd = self.command_pipe.recv()
            print "WORKER " + str(self.gpu_id) + " GOT CMD:", cmd[:1]
            if cmd[0] == 'gauss_newton':
                message, batches, new_batch_map, damping, mask = cmd[:5]
            else:
                message, batches, new_batch_map, mask = cmd[:4]

            # we always receive a new batch map, unless its a gauss-newton request.
            if message == 'grad' or message == 'losses':
                assert new_batch_map is not None

            if new_batch_map is not None:
                self.batch_map = new_batch_map

            # invariant: np_X always has the current value of the parameters.
            # becasue np_X is shared memory. That np_X is up-to-date must be enforced
            # by the manager.
            X = to_gpu(self.np_X)

            if message == 'quit':
                print 'WORKER ' + str(self.gpu_id) + ' QUIT'
                self.ans_pipe.send(('quit', ))
                break

            if message == 'cycle_data':
                self.dp.cycle_data()
                self.ans_pipe.send(('cycle_data', ))

            elif message == 'forget':
                self.dp.forget()
                super(Worker, self).gauss_newton('forget')
                self.ans_pipe.send(('forget', ))

            elif message == 'grad':
                if mask:
                    new_X = (X * g.tile(mask, (X.shape[0]/mask.shape[1],))).ravel()
                else:
                    new_X = X.ravel()
                g_ans = mcpu(self.grad(batches, new_X, mask=mask))
                self.ans_pipe.send(('grad', g_ans))

            elif message == 'accuracy':
                if mask:
                    raise Exception('Dropout not implemented for accuracy calculations yet')
                a_ans = mcpu(self.get_accuracy(batches, X))
                self.ans_pipe.send(('accuracy', a_ans))

            elif message == 'losses':
                if mask:
                    new_X = (X * g.tile(mask, (X.shape[0]/mask.shape[1],))).ravel()
                else:
                    new_X = X.ravel()
                l_ans = mcpu(self.losses(batches, new_X, mask=mask))
                self.ans_pipe.send(('losses', l_ans))

            elif message == 'get_validation_data':
                data = self.dp.validation_data
                self.ans_pipe.send(('get_validation_data', data))

            elif message == 'cross_validate':
                # a note on l_ans here...
                # it ends up being a list of tuples
                # each tuple has: Hidden activations, Pre-softmax output

                # new_X = (X * g.tile(mask, (X.shape[0]/mask.shape[1],))).ravel()
                l_ans = mcpu(self.forward_pass(batches, X, validate=True, mask=mask))
                self.ans_pipe.send(('cross_validate', l_ans))

            elif message == 'gauss_newton':
                self.gauss_newton_order = not self.gauss_newton_order
                if self.gauss_newton_order:
                    batches = batches[::-1]
                # why do we have the order variable?
                # It is sensible when len(batches) is small,
                # say 2 or 3 (but is pointless when larger).
                # If len(batches)==3, we'll get the batches
                # in the order 1,2,3,3,2,1,1,2,3,3,2,1,
                # and won't need to recompute the state
                # at the 2nd occurrance of 3, and the second occurance of 1.
                # If the state recomputation takes half
                # of the gauss-newton function, then we're talking about
                # 1/3 of the batches * 1/2 of the time = about 10% speedup.
                # If we use 2 minibatches for the curvature,
                # we'll be in 1,2,2,1,1,2,2,1, we'll be
                # saving the computation in 1/2 of the batches,
                # thus obtaining a 25% speedup. Which is decent.

                R = to_gpu(self.np_R)
                # we get the argument, R, through the shared variable.

                # the damping is given in the third command
                damping = cmd[3]

                if mask:
                    new_X = (X * g.tile(mask, (X.shape[0]/mask.shape[1],))).ravel()
                else:
                    new_X = X.ravel()
                #try:
                gn_ans, gn_tot = self.gauss_newton(batches, new_X, R, damping, mask)
                #except:
                #    ans_pipe.send(('quit_now', 'numerically_unstable'))

                # copy the answer to the shared memory
                self.np_MY_ANS[:] = gn_ans.asarray()

                # and tell the manager that we are done, reporting the minibatch size.
                self.ans_pipe.send(('gauss_newton', gn_tot))

            else:
                raise TypeError('message (%s) is of an unrecognized kind.' % message)

    def inc_total_batches(self):
        with self.total_batches_lock:
            self.total_batches.value += 1
        return self.total_batches.value

    def get_batch(self, bid, valid=False):
        total_batches = self.inc_total_batches()

        if valid:
            ans = self.dp.get_valid_batch(bid)

        # if we're interested in the test set, we don't repermute anything.
        elif bid < 0:
            batch_id = bid
            ans = self.dp(batch_id)

        # if we're about the grad / curvature / whatever set, then we repermute.
        else:
            batch_id = self.batch_map[bid]
            ans = self.dp(batch_id)

        bid_sig = self.dp.sig(batch_id)
        print 'total batches: %s worker_id: %s (batchid=%s; sig=%s)' % (
            total_batches, self.worker_id, bid, bid_sig)

        return ans

    def get_accuracy(self, batches, X):
        tot_accuracy_for_each_ts = []
        cms = []
        tot_weights = []
        for bid in batches:
            batch = self.get_batch(bid)
            accuracy_for_each_ts, confusion, weights = super(Worker, self).get_accuracy(batch, X)
            cms.append(confusion)
            tot_accuracy_for_each_ts.append(accuracy_for_each_ts)
            tot_weights.append(weights)

        # below merges results for each batch before sending back to c3_par_c
        if len(tot_accuracy_for_each_ts) > 1:
            tot_weights = to_masked(tot_weights)
            tot_accuracy_for_each_ts = np.ma.average(to_masked(tot_accuracy_for_each_ts), axis=0, weights=tot_weights)
            #tot_accuracy_for_each_ts = to_masked(tot_accuracy_for_each_ts).mean(axis=0)
            tot_accuracy_for_each_ts = np.array(tot_accuracy_for_each_ts)
            tot_weights = np.array(tot_weights.sum(axis=0))
            confusion = defaultdict(Counter)
            for cm in cms:
                for k, v in cm.iteritems():
                    confusion[k].update(v)
        else:
            tot_accuracy_for_each_ts = tot_accuracy_for_each_ts[0]
            tot_weights = tot_weights[0]

        return tot_accuracy_for_each_ts, confusion, tot_weights

    def grad(self, batches, X, mask):
        tot_grad, tot_losses, tot_grad2, tot = 0,0,0,0
        for bid in batches:
            batch = self.get_batch(bid)
            batch_size = self.dp.size(batch)
            grad, grad2, losses = super(Worker, self).grad_grad2_losses(batch, X,
                                                                        mask=mask)
            tot += batch_size
            tot_grad += grad
            tot_grad2 += grad2
            tot_losses += losses
        return tot_grad, tot_grad2, tot_losses, tot

    def losses(self, batches, X, mask):
        tot_losses, tot = 0., 0
        for bid in batches:
            batch = self.get_batch(bid)
            batch_size = self.dp.size(batch)
            losses = super(Worker, self).losses(batch, X, mask=mask)
            tot += batch_size
            tot_losses += losses
        return tot_losses, tot

    def forward_pass(self, batches, X, validate=False, mask=None):
        activations = []
        for bid in batches:
            batch = self.get_batch(bid, valid=validate)
            (V, A, B, H, OX) = super(Worker, self).forward_pass(batch, X, mask=mask)
            activations.append([[x.asarray() for x in H[:3]], (bid, [x.asarray() for x in OX])])
        return activations

    def gauss_newton(self, batches, X, R, damping, mask):
        tot_gn, tot = 0, 0
        for bid in batches:
            batch = self.get_batch(bid)
            batch_size = self.dp.size(batch)
            gn = super(Worker, self).gauss_newton(bid, batch, X, R,
                                                  damping, mask=mask)
            tot_gn += gn
            tot += batch_size
        return tot_gn, tot
