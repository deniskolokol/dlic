import os
import sys
import traceback
import numpy as np
from collections import Counter, defaultdict
from multiprocessing.queues import SimpleQueue

import ersatz.mrnn.opt.hfs.c3c as c3c
from ersatz.listener import Consumer
from ersatz.exception import ApiParamsError
from ersatz import conf
from ersatz.mrnn.util import (shmem_as_ndarray, partition_batches,
                              cpu, grab_gpu_boards,
                              to_masked_array_of_different_len as to_masked)
from  ersatz.mrnn.opt.hfs.c3c import (std_backtrack_arithmetic_factory,
                                      progress_heuristic,
                                      damping_heuristic)

from ersatz.exception import MRNNWorkerException, UnstableModelException
from ersatz import get_logger
from ersatz.misc import Tee
from ersatz.reporter import build_train_pipe

log = get_logger('c3_par_c')


class HF(c3c.HF):
    # c3_par_c inherits from c3c, and it reimplements the __init__, grad, loss, gauss_newton
    # functions with parallel versions. I won't comment much on it except that
    # It's kind of cool and I'm proud of it, mainly because it's so simple and easy.
    def __init__(self,
                 path,
                 grad_batches,
                 GN_batches,
                 line_search_batches,

                 RHO_nom_str,
                 RHO_denom_str,
                 BT_fn_str,
                 STOP_fn_str,

                 cg_prep_exprs,

                 cg_max_cg,

                 backtrack_iter_set,

                 cg_min_cg = 1,
                 maxnum_iter=1000,
                 maxnum_cg=100000,

                 cg_shrink_factor=.95,
                 cg_damper_expr='damp',
                 cg_precond_expr='(grad2 + damp)**.75',

                 cg_stop_thresh_factor=1.,

                 progress_heuristic=progress_heuristic,
                 damping_heuristic=damping_heuristic,
                 test_freq=1,
                 test_otherwise_on_num=None,

                 save_freq=None,
                 settings={},
                 rotate_data_after=10,
                 use_dropout=True,
                 worker_params=None,
                 number_of_timesteps_to_use=9999999,
                 train_pipe_param=None,
                 ):

        self.number_of_timesteps_to_use = number_of_timesteps_to_use
        # we're gonna do the usual init blah
        self.consumer = Consumer(default_queue=worker_params['queue_key'])
        self.is_model_resumed = False
        self.save_freq = save_freq
        self.cg_min_cg = cg_min_cg
        self.settings = settings
        self.rotate_data_after = rotate_data_after
        self.use_dropout = use_dropout
        self.model_id = worker_params['id']
        self.queue_key = worker_params['queue_key']
        self.resume_cost = None

        ### maintain two files, one for a high-level overview, the other for the guts of cg.
        self.path = path
        from ersatz.mrnn.opt.utils.printing import make_cg_printf
        self._printf, self._printf_cg = make_cg_printf(
            os.path.join(conf.settings.WORKING_DIR, 'models/' + path.replace('.','/')))
        def printf(x, detail=False):
            if detail is False:
                self._printf(x)
                self._printf_cg(x)
            else:
                self._printf_cg(x)

        self.printf = printf

        self.grad_batches = grad_batches
        self.GN_batches = GN_batches
        self.line_search_batches = line_search_batches

        # how to evaluate various things?
        self.RHO_nom_str = RHO_nom_str
        self.RHO_denom_str = RHO_denom_str
        self.BT_fn_str = BT_fn_str
        self.STOP_fn_str = STOP_fn_str

        self.cg_prep_exprs = cg_prep_exprs


        self.cg_damper_expr = cg_damper_expr
        self.cg_precond_expr = cg_precond_expr

        self.maxnum_iter = maxnum_iter
        self.maxnum_cg = maxnum_cg

        self.cg_max_cg = cg_max_cg
        self.cg_shrink_factor = cg_shrink_factor

        self.damping_heuristic = damping_heuristic
        self.progress_heuristic = progress_heuristic
        self.backtrack_iter_set = backtrack_iter_set
        self.behavior_at_max_damping = settings.behavior_at_max_damping
        self.max_damping = settings.max_damping

        self.cg_stop_thresh_factor = cg_stop_thresh_factor


        ####
        self._total_num_cg = 0
        self._total_batch = 0

        self.iter = 1
        self.test_freq = test_freq
        self.test_otherwise_on_num = test_otherwise_on_num
        self.test_losses = -1
        self.cheap_test_losses = -1



        #### The multiprocessing:
        self.gpu_boards = grab_gpu_boards()

        for x in self.gpu_boards:
            if x == -1:
                raise Exception ("not enough available GPUs. Quitting.")


        def info_provider(board_id, settings, ans_pipe):
            print 'info_provider: calling init function.'
            log.debug('INFO PROVIDER process PID: %s' % (os.getpid(), ))
            from ersatz.mrnn.worker import BaseWorker

            try:
                worker = BaseWorker(0, board_id, settings)
            except Exception as e:
                traceback.print_exc()
                ans_pipe.send(('ERROR', e, None, None, None, None, None))
            else:
                ans_pipe.send((worker.message, cpu(worker.init_X),
                               worker.train_batches, worker.test_batches,
                               worker.init_damping, worker.dp.__repr__(),
                               worker.W.__repr__()))
            finally:
                ans_pipe.close()
                print 'info_provider: sent the needed items through the pipe. Done.'


        import multiprocessing
        info_pipe, info_pipe2 = multiprocessing.Pipe()
        info_guy = multiprocessing.Process(
            target=info_provider, args=(self.gpu_boards[0], settings, info_pipe2))
        info_guy.start()
        pipe_data = info_pipe.recv()
        info_guy.join()
        info_pipe.close()
        self.message = pipe_data[0]
        if self.message == 'ERROR':
            exc = pipe_data[1]
            raise exc
        _, init_X_np, train_batches, test_batches, init_damping, batch_fn, W = pipe_data

        # OK. We've now got stuff from the info provider.
        self.printf('\n%s\n\n' % self.message)

        ###<-- This is a cheat. we don't have access to batch fn nor to W. But we don't really care, as long
        ### as we get their strings and know how to display them.
        self.batch_fn = batch_fn
        self.W = W
        if type(self.W) is str:
                    W_arr = self.W.split('\n')
                    self.v = int(W_arr[1].split('=')[1])
                    self.h = int(W_arr[2].split('=')[1])
                    self.f = int(W_arr[3].split('=')[1])
                    self.o = int(W_arr[4].split('=')[1])


        # now we're gonna make the "shared" variables where we write
        # the answers back form the GN process guys. I don't bother with the
        # gradients cause they take so much time that sending stuff through a pipe
        # is good enough.


        init_X_np = init_X_np.astype(np.float32)
        print 'init_X_np size = ', init_X_np.size

        # create the shared memory for X, R, and
        # the answers where the GN calculations write their answers.
        X_shared = multiprocessing.Array('f', init_X_np)
        R_shared = multiprocessing.Array('f', init_X_np * 0)

        # each process has its shared variable,
        # where it will write its gauss-newton result.
        GN_shared = [None] * len(self.gpu_boards)
        for i in range(len(self.gpu_boards)):
            GN_shared[i] = multiprocessing.Array('f', init_X_np * 0)

        # Unfortunately, shmem_as_ndarray is stupid, returning
        # too large arrays; so we trim by len(init_X_np).
        # That seems to do the trick.
        # sh_X: the shared variable of the current setting
        # of the parameters
        self.sh_X = shmem_as_ndarray(X_shared)[:len(init_X_np)]

        # sh_R: the shaerd variable of the current R
        # value that's gotta be used by the gauss-newton guys.
        self.sh_R = shmem_as_ndarray(R_shared)[:len(init_X_np)]

        # the answer variables where the processes
        # write their gauss-newton answers to.
        self.GN_shared_list = [shmem_as_ndarray(x)[:len(init_X_np)]
                               for x in GN_shared]


        # create the processes.
        self.command_pipe = \
            [multiprocessing.Pipe() for i in range(len(self.gpu_boards))]
        self.ans_pipe = \
            [multiprocessing.Pipe() for i in range(len(self.gpu_boards))]
        self.workers = \
            [None] * len(self.gpu_boards)

        def run_worker(worker_id, gpu_id, settings, command_pipe,
                       ans_pipe, error_queue, train_pipe_param, *args, **kwargs):
            if train_pipe_param:
                worker_train_pipe = build_train_pipe(*train_pipe_param)
                sys.stdout = Tee('stdout', worker_train_pipe)
                sys.stderr = Tee('stderr', worker_train_pipe)

            from ersatz.mrnn.worker import Worker
            try:
                worker = Worker(worker_id, gpu_id, settings, command_pipe, ans_pipe,
                                *args, **kwargs)
            except Exception:
                traceback.print_exc()
                ans_pipe.send(('ERROR', traceback.format_exc))
                ans_pipe.close()
            else:
                ans_pipe.send(('INITED', None))
                try:
                    worker.run()
                except MemoryError:
                    exc = MRNNWorkerException(
                        'Not enough memory for this dataset and model parameters.',
                        show_to_user=True,
                        original_traceback=traceback.format_exc())
                    error_queue.put(exc)
                except Exception as e:
                    traceback.print_exc()
                    error_queue.put(e)
            finally:
                if train_pipe_param:
                    sys.stdout.close()
                    sys.stderr.close()

        total_batches = multiprocessing.Value('l', 0)
        total_batches_lock = multiprocessing.Lock()

        self.error_queue = SimpleQueue()
        for i in range(len(self.gpu_boards)):
            self.workers[i] = multiprocessing.Process(
                target=run_worker,
                args=(i,
                      self.gpu_boards[i],
                      settings,
                      self.command_pipe[i][1],
                      self.ans_pipe[i][1],
                      self.error_queue,
                      train_pipe_param,
                      init_X_np.size,
                      X_shared,
                      R_shared,
                      GN_shared,
                      total_batches,
                      total_batches_lock))

            # get them going and waiting for commands.
            self.workers[i].start()

        self.check_workers_inited(self.workers, self.command_pipe, self.ans_pipe)
        print 'manager: started all workers.'




        # the functions: we don't ever call them ourselves,
        # we only do things through the processes.
        # self.losses_fn = losses_fn
        # self.grad_grad2_losses_fn = grad_grad2_losses_fn
        # self.gauss_newton_fn = gauss_newton_fn
        # self.data = self.batch_fn = batch_fn


        ## the batch sets
        self.train_batches = train_batches
        self.test_batches = test_batches
        if len(self.train_batches) > len(grad_batches):
            self.grad_batches = grad_batches
        else:
            self.grad_batches = self.train_batches

        if len(self.train_batches) > len(GN_batches):
            self.GN_batches = GN_batches
        else:
            self.GN_batches = self.train_batches

        if len(self.train_batches) > len(self.line_search_batches):
            self.line_search_batches = line_search_batches
        else:
            self.line_search_batches = self.train_batches

        # TODO: fix it, for BT_batches we don't need all train batches,
        # but we selects number of train batches equal to num of gpu
        # so we can run BT on smaller number of batches
        self.cg_prep_exprs = ['loss_0_GN = loss(0, batches=GN_batches)', 'BT_batches = range(0,' + str(len(self.train_batches)) + ')']



        # now we import gnumpy ourselves, and make
        # this process, the one
        # that makes all the decisions,
        # have its own GPU. It will be sharing it with a worker, but it's ok
        # beacuse they won't be running kernels simultaneously due to the way
        # they're synchronized.


        from ersatz.mrnn import gnumpy as g
        print 'initializing the GPU right here, for the boss process (who doesn\'t call init_function).'
        g.board_id_to_use = self.gpu_boards[0]
        g._init_gpu()

        self.X = g.garray(init_X_np)
        #self.W = W
        self.damping = 1*init_damping
        self.init_damping = init_damping
        self.CG_x = self.X*0
        if self.use_dropout:
            self.refresh_mask()
        else:
            self.mask = None

        print ('manager: has set up my own gpu, which is also shared with the first worker. '
               'Now will ask the first worker for some guidance.')

        # the basics:
        # the initial CG solution
        print 'manager: got all the init info from all workers.'

    def get_ans(self, worker_id):
        def check_error():
            if not self.error_queue.empty():
                exc = self.error_queue.get()
                raise exc
        while True:
            check_error()
            if self.ans_pipe[worker_id][0].poll(0.001):
                return self.ans_pipe[worker_id][0].recv()

    def refresh_mask(self):
        from ersatz.mrnn import gnumpy as g
        self.mask = (g.rand((1, self.h))>.5)


    def check_workers_inited(self, workers, command_pipe, ans_pipe):
        """
        waiting 3 minutes for first worker initing if worker doesn't response
        shutdown all workers
        """
        for i in range(len(self.gpu_boards)):
            response = self.ans_pipe[i][0].recv()
            if response[0] == 'ERROR':
                #TODO: response[1] contains traceback
                self.shutdown_workers()
                raise ApiParamsError('Can\'t initializate workers',
                                     original_traceback=response[1])

    def shutdown_workers(self):
        for i in range(len(self.gpu_boards)):
            self.command_pipe[i][0].send(('quit', None, None, None))
        for i in range(len(self.gpu_boards)):
            self.workers[i].join()


    def grad(self, batches, X):
        self._total_batch += 1
        import time
        start_grad = time.time()

        #batches = range(min(len(batches), len(self.batch_map)))

        from ersatz.mrnn import gnumpy as g

        # communicate the current setting of the parameters:
        self.sh_X[:] = X.asarray()

        print "GPU BOARDS", self.gpu_boards
        for i in range(len(self.gpu_boards)):
            batches_i = partition_batches(batches, i, len(self.gpu_boards))

            # send the requests
            if any(x<0 for x in batches):
                self.command_pipe[i][0].send(
                    ('grad', batches_i, self.batch_map_test, self.mask))
            else:
                self.command_pipe[i][0].send(
                    ('grad', batches_i, self.batch_map, self.mask))


        tot_grad, tot_losses, tot_grad2, tot = 0, 0, 0, 0
        for i in range(len(self.gpu_boards)):
            # grad sends the answer through a pipe
            cmd_name, (tot_grad_i,
                       tot_grad2_i,
                       tot_losses_i,
                       tot_i) = self.get_ans(i)

            assert cmd_name == 'grad'
            tot_grad += g.garray(tot_grad_i)
            tot_grad2 += g.garray(tot_grad2_i)
            tot_losses += tot_losses_i
            tot += tot_i

        end_grad = time.time()
        self.printf('HF: time per grad minibatch = %12.6f\n' % ((end_grad - start_grad) / float(len(batches))))


        self.tot_batch_size = tot
        return (tot_grad / tot), (tot_grad2 / tot), (tot_losses / tot)


    def get_accuracy(self, batches, X):

        self.sh_X[:] = X.asarray()

        for i in range(len(self.gpu_boards)):
            batches_i = partition_batches(batches, i, len(self.gpu_boards))

            self.command_pipe[i][0].send(
                ('accuracy', batches_i, self.batch_map, self.mask))

        accuracy_for_each_ts = []
        accuracy_total = []
        accuracy_for_last_10_steps = []
        weights = []
        confusion = defaultdict(Counter)
        for i in range(len(self.gpu_boards)):
            cmd_name, (acc_for_each_ts, cm, w) = self.get_ans(i)
            accuracy_for_each_ts.append(acc_for_each_ts)
            weights.append(w)
            for k, v in cm.iteritems():
                confusion[k].update(v)

        assert cmd_name == 'accuracy'

        accuracy_for_each_ts = to_masked(accuracy_for_each_ts)
        weights = to_masked(weights)
        accuracy_for_each_ts = np.array(np.ma.average(accuracy_for_each_ts,
                                                      axis=0, weights=weights))
        weights = np.array(weights.sum(axis=0))
        accuracy_total = np.average(accuracy_for_each_ts, weights=weights)
        accuracy_for_last_10_steps = accuracy_for_each_ts[-10:]

        return (accuracy_for_each_ts.tolist(), accuracy_total,
                accuracy_for_last_10_steps.tolist(), confusion)


    def losses(self, batches, X):
        self._total_batch += 1
        #batches = self._dynamic_blowup(batches)


        # communicate the current parameters:
        self.sh_X[:] = X.asarray()

        for i in range(len(self.gpu_boards)):
            batches_i = partition_batches(batches, i, len(self.gpu_boards))

            self.command_pipe[i][0].send(
                ('losses', batches_i, self.batch_map, self.mask))

        # then collect the answers:
        tot_losses, tot = 0, 0
        for i in range(len(self.gpu_boards)):
            # losses also get their answer through a pipe.
            cmd_name, (tot_losses_i,
                       tot_i) = self.get_ans(i)

            assert cmd_name == 'losses'
            tot_losses += tot_losses_i
            tot += tot_i

        self.tot_batch_size = tot
        return tot_losses / tot

    def gauss_newton(self, batches, X, R):
        self._total_batch += 1
        #batches = self._dynamic_blowup(batches)

        from ersatz.mrnn import gnumpy as g

        # just copy the damn parameters. Make it faster later if I really want to.
        self.sh_X[:] = X.asarray()

        # also copy R.
        self.sh_R[:] = R.asarray()
        for i in range(len(self.gpu_boards)):
            batches_i = partition_batches(batches, i, len(self.gpu_boards))

            self.command_pipe[i][0].send(
                ('gauss_newton', batches_i, None, self.damping, self.mask))



        # now get the answer back. Of course.
        tot_gn, tot = 0, 0
        for i in range(len(self.gpu_boards)):
            cmd_name, tot_i = self.get_ans(i)
            if cmd_name == 'quit_now':
                #import sys
                #sys.exit('model became numerically unstable, exiting...')
                raise UnstableModelException('model became numerically unstable, exiting...')
            assert cmd_name == 'gauss_newton'

            tot += tot_i
            # get the result of the gauss newton thing
            # from the shared memory:
            tot_gn += g.garray(self.GN_shared_list[i])

        self.tot_batch_size = tot
        return (tot_gn / tot)


    def update_batches(self):
        # maintain a big permutation of the batch map.
        # IT's also possible to shift-left the whole permutation.
        self.batch_map = np.random.permutation(len(self.train_batches))
        self.batch_map_test = np.random.permutation(len(self.test_batches)) * -1. - 1
        #print "TRAIN BATCHES: %s" % str(len(self.train_batches))
        #print "train batches: %s" % str(self.train_batches)

        # tell them to forget:
        for i in range(len(self.gpu_boards)):
            self.command_pipe[i][0].send(('forget', None, None, None))

        # and make sure they did.
        for i in range(len(self.gpu_boards)):
            msg, = self.get_ans(i)
            assert msg == 'forget'

    def get_validation_data(self):
        self.command_pipe[0][0].send(('get_validation_data', None, None, None))
        msg,data = self.get_ans(0)
        assert msg == 'get_validation_data'
        return data

    def cycle_data(self):
        for i in range(len(self.gpu_boards)):
            self.command_pipe[i][0].send(('cycle_data', None, None, None))

        for i in range(len(self.gpu_boards)):
            msg, = self.get_ans(i)
            assert msg == 'cycle_data'

    def cross_validate(self, batches, X):
        for i in range(len(self.gpu_boards)):
            batches_i = partition_batches(batches, i, len(self.gpu_boards))
            if self.use_dropout:
                self.command_pipe[i][0].send(('cross_validate', batches_i, self.batch_map, 'validate'))
            else:
                self.command_pipe[i][0].send(('cross_validate', batches_i, self.batch_map, None))

        return_data = []
        for i in range(len(self.gpu_boards)):
            msg, data = self.get_ans(i)
            assert msg == 'cross_validate'
            return_data.append(data)


        return return_data


