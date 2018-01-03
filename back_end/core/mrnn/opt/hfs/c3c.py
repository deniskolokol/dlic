"""
This is the file that implements the HF optimizer.

We are making it support multi-GPU code, so we are careful
to not import gnumpy before we fork the processes (but for more
details you should see opt.hfs.c3_par_c which does the parallelization
stuff (but it inherits from this class), so this one does most of the
heavy lifting.
"""

import os
import time
import sys
import traceback
import cPickle as pickle
import json
import copy
import numpy as np
from termcolor import colored
from ersatz import conf, api, aws
from ersatz.exception import UnstableModelException, ApiStoppedTraining
from ersatz.misc import NPArrayEncoder


# utility functions:
def ip(x,y): return (x*y).sum()
def norm2(x): return ip(x,x)
def norm(x): return float(np.sqrt(norm2(x)))
def normalize(x, M_diag=None):
    if M_diag is None:
        n = norm(x)
    else:
        n = float(np.sqrt(ip(x,M_diag*x)))
    return n, x/n


#### backtracking: classes for the CG backtracking
#### (see original HF paper)
class std_backtrack_geometric_factory(object):
    def __init__(self, inext=50, istep=1.3):
        self.inext = inext
        self.istep = istep
    def __call__(self, i):
        ii = float(self.inext)

        while ii <= i:
            if int(ii) == i:
                return True
            if int(ii) > i:
                return False
            ii *= self.istep

    def __repr__(self):
        return """Geometric backtrack set
        inext = %s
        istep = %s""" % (self.inext, self.istep)


class std_backtrack_arithmetic_factory(object):
    def __init__(self, freq=15):
        self.freq = freq
    def __call__(self, i):
        return i % self.freq == 0
    def __repr__(self):
        return """Arithmetic backtrack set:
        freq = %s """ % self.freq


### a function that decides when to stop CG.
def progress_heuristic(losses):
    eps = 0.0005

    i = len(losses)
    k = int(max(10, 0.1*i))

    if len(losses) < k+1:
        return False

    phi_x_i   = losses[-1]
    phi_x_imk = losses[-1-k]

    if i>k and phi_x_i<0 and (phi_x_i-phi_x_imk)/phi_x_i < k*eps:
        return True
    else:
        return False


## a function that helps us with the damping heuristic
def damping_heuristic(damping, rho, max_damping, behavior_at_max_damping):
    from numpy import isnan
    drop = 4./5 #2./3
    boost = 1./drop

    if rho < 1/4. or isnan(rho):
        d = boost
    elif rho > .7:
        d = drop
    else:
        d = 1.
    if damping[0] > max_damping[0] or damping[1] > max_damping[1]:
        return damping * behavior_at_max_damping
    else:
        return damping*d



class HF(object):
    def __init__(self,
                 # the path where to save the logs
                 path,

                 # the init function returns all of the
                 # parameters. You can find examples in the
                 # text
                 init_function,

#                the init function returns all that
#                  message,

#                  init_X,
#                  W,

#                  # core functions
#                  losses_fn,
#                  grad_grad2_losses_fn,
#                  gauss_newton_fn,

#                  batch_fn,

#                  # batches
#                  train_batches,
#                  test_batches,
#                  init_damping,


                 # NOTE on the minibatch list: the grad minibatch
                 # is evaluated on a list of batches.
                 # But the meaning of these batches depends on the
                 # data object, which is asked to change the meaning
                 # of the indexes in the call to the forget function
                 # below (in the update_batches function).

                 # the list of minibatches on which the gradient is computed
                 grad_batches,
                 # the list of minibatches on which the curvature is computed
                 GN_batches,

                 # the list of minibatches on which the linesearches
                 # are conducted
                 line_search_batches,

                 # the string for evaluating the numerator of the
                 # expression for the reduction ratio rho (see a run file)
                 RHO_nom_str,
                 # similarly for the denominator
                 RHO_denom_str,
                 # an expression for deciding on how to backtrack CG
                 # (see also the original HF paper)
                 BT_fn_str,
                 # an expression that helps us decide on when to stop
                 # CG.
                 STOP_fn_str,

                 # I basically don't use this var
                 cg_prep_exprs,


                 # an absolute limit on the number of CG steps
                 cg_max_cg,

                 # the set of points over which we backtrack
                 backtrack_iter_set,

                 # selfexplanatory: (though this module must have it
                 # one).
                 # the one define in opt.hfs.c3_par_c allows for
                 # num_gpus to be greater than one.
                 num_gpus = 1,

                 # how many HF steps before tremination?
                 maxnum_iter=1000,
                 # how many CG steps before termination?
                 maxnum_cg=100000,

                 # When we initialize CG, we shrink the initial
                 # solution by .95. It helps.
                 cg_shrink_factor=.95,

                 # the expression for damping: damp is spherical.
                 cg_damper_expr='damp',

                 # the expression for the precnoditioner
                 cg_precond_expr='(grad2 + damp)**.75',

                 # I don't ever touch it. If you like, see the code
                 cg_stop_thresh_factor=1.,

                 # an absolute limit on the smallest number of CG steps
                 cg_min_cg = 1,

                 progress_heuristic=progress_heuristic,
                 damping_heuristic=damping_heuristic,
                 test_freq=1,
                 test_otherwise_on_num=None,
                 save_freq=None,

                 grab_gpus=True,
                 settings={},
                 rotate_data_after=10,
                 use_dropout=True,
                 worker_params=None,
                 number_of_timesteps_to_use=9999999
                 ):

        self.number_of_timesteps_to_use = number_of_timesteps_to_use
        self.is_model_resumed = False
        self.save_freq = save_freq
        self.cg_min_cg = cg_min_cg
        assert num_gpus == 1
        self.num_gpus = num_gpus
        self.rotate_data_after = rotate_data_after
        self.use_dropout = use_dropout

        self.model_id = worker_params['id']

        from ersatz.mrnn.opt.hfs.par import utils as par_utils
        if grab_gpus:
            board_id = par_utils.grab_a_gpu_board()
            if board_id==-1:
                print 'cant grab a gpu board. quitting. try again later.'

        (self.message,
         init_X,
         self.W,
         self.losses_fn,
         self.grad_grad2_losses_fn,
         self.gauss_newton_fn,
         self.batch_fn,
         self.train_batches,
         self.test_batches,
         self.init_damping,
         self.get_accuracy_fn) = init_function(0, board_id, ret=True)

        self.damping = 1*self.init_damping
        self.settings = settings

        # maintain two files, one for a high-level overview, the other for the guts of cg.
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
        self.printf('\n%s\n\n' % self.message)

        from ersatz.mrnn import gnumpy as g
        self.X = g.garray(init_X)

        #self.damping = 1*init_damping
        #self.init_damping = init_damping
        self.CG_x = self.X*0

        self.data = self.batch_fn

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

        self.cg_stop_thresh_factor = cg_stop_thresh_factor



        ####
        self._batch_offset = 0
        self._total_num_cg = 0
        self._total_batch = 0
        self.iter = 1
        self.test_freq = test_freq
        self.test_otherwise_on_num = test_otherwise_on_num
        self.test_losses = -1
        self.cheap_test_losses = -1



    # _op: the (single gpu) function that computes a
    # loss/grad/curvature objective.
    def _op(self, batches, func):
        self._total_batch += 1
        def shift(b):
            if b >= 0:
                return (b + self._batch_offset) % len(self._train_batches)
            else:
                return b

        def incr(ans,b):
            from ersatz.mrnn import gnumpy as g
            if ans==[]:
                if isinstance(b, (np.ndarray, g.garray)):
                    ans.append(1*b)
                else:
                    for bx in b:
                        ans.append(bx)
            else:
                if isinstance(b, (np.ndarray, g.garray)):
                    ans[0]+=b
                else:
                    assert len(ans)==len(b)
                    for (ax,bx) in zip(ans,b):
                        ax+=bx
        def div(ans, c):
            from ersatz.mrnn import gnumpy as g
            for i in range(len(ans)):
                ans[i]/=c
            if len(ans)==1 and isinstance(ans[0], (np.ndarray, g.garray)):
                return ans[0]
            else:
                return tuple(ans)
        ans = []
        tot = 0.
        for b in map(shift, batches):
            d = self.batch_fn(b)
            tot += self.batch_fn.size(d)
            incr(ans, func(b,d))

        return div(ans,tot)

    # compute the loss on a set of batches
    def losses(self, batches, X):
        def func(b,d):
            return self.losses_fn(d, X)
        return self._op(batches, func)

    def detailed_losses(self, batches, X):
        ans = []
        sizes = []
        for b in batches:
            d = self.batch_fn(b)
            ans.append(self.losses_fn(d, X))
            sizes.append(self.batch_fn.size(d))
        return ans, sizes

    # compute the grad over the set of batches. It may
    # also return grad2, which is an approximation to the sum
    # of the squares of the gradient.
    def grad(self, batches, X):
        start_grad = time.time()

        def func(b,d):
            return self.grad_grad2_losses_fn(d, X)
        ans =  self._op(batches, func)


        end_grad = float(time.time())
        self.printf('HF: time per grad minibatch = %12.6f\n' % ((end_grad - start_grad) / len(batches)))

        return ans

    # R is the vector we multiply by
    def gauss_newton(self, batches, X, R):
        if 'order' not in self.__dict__:
            self.order = True
        self.order = not self.order

        if self.order:
            # change the order of the batches to make state caching more feasible.
            batches = batches[::-1]

        def func(b,d):
            # note that we pass the self.damping parameters to the
            # gauss_newton_fn, so that it'll know how much structural
            # damping to use.
            return self.gauss_newton_fn(b, d, X, R, self.damping)
        return self._op(batches, func)


    def update_batches(self):
        # minibatch cycling (as opposed to the train permutation map).
        self._batch_offset += len(self.GN_batches)
        if self._batch_offset >= len(self._train_batches):
            self._batch_offset = 0
            # but _batch_offest isn't really important in our setting.
            # you can easily ignore it

        self.batch_fn.forget()# <-- this is important (use a different
                              # minibatch next time
        self.gauss_newton_fn('forget') # <-- while this thing asks the
                              # gauss-newton function to forget its
                              # cached hidden state.


    def cycle_data(self):
        #pretty sure this doesn't actually get called because it's overridden...
        self.batch_fn.cycle_data()

    ################################################################
    def calc_precond_and_damper(self, grad, grad2):
        damp = float(self.damping[0])

        env = dict(grad = grad,
                   grad2 = grad2,
                   damp = damp,
                   np = np,
                   norm = norm,
                   ip = ip)

        precond = eval(self.cg_precond_expr, env)
        damper = eval(self.cg_damper_expr, env)
        return precond, damper


    def get_new_direction(self, grad, grad2):
        # here we take grad and grad2 (which is the
        # basis of the preconditioner) and return the parameter
        # update.

        b = -grad

        self.precond, self.damper = \
            self.calc_precond_and_damper(grad, grad2)

        def A(x, batches=None):
            if batches is None: batches=self.GN_batches
            return self.gauss_newton(batches, self.X, x) + x*self.damper

        def M_inv(x):
            return x/self.precond


        # OK! Call CG.

        return self.cg(b = b,
                       A = A,
                       M_inv = M_inv,
                       x0 = self.CG_x)


    def _model(self, x, batches=None, r=None, damp=None):
        # here we evaluate the quadratic model on various minibatches
        # and with or without damping
        assert damp is not None
        assert (r is None)^(batches is None)

        if r is None:
            r = self._b - self._A(x,batches)

        ans = -ip(self._b+r,x)*0.5
        if damp is False:
            ans -= ip(x,self.damper*x)*0.5

        return ans

    def _loss(self, x, batches):
        # here we evaluate the loss
        return self.losses(batches, self.X + x)

    def cg(self, b, A, M_inv, x0):
        # here we run CG
        GN_batches = self.GN_batches

        ### python hacks to ensure that _model and _loss are doing the right thing.
        self._b = b
        self._A = A
        model = self._model
        loss = self._loss

        # prepare a bunch of variables to our namespace.
        for expr in self.cg_prep_exprs:
           print "Executing expression", expr
           exec expr


        model_losses = []

        # for CG backtracking and stopping.

        BT_x = 1*x0
        stop_best = np.inf ; stop_val = -1
        BT_best = np.inf   ; BT_val = -1; BT_i = 0;

        ################ start CG
        x = x0
        r = b-A(x)
        Mr = M_inv(r)
        d = 1*Mr

        start_cg = time.time()

        # OK: Do the CG
        for i in range(self.cg_max_cg):
            if i % 3 == 0 and self.consumer.check_stop_message():
                raise ApiStoppedTraining()

            Ad=A(d) #### EXPENSIVE
            dAd = ip(d,Ad)
            alpha = ip(r,Mr)/dAd

            beta_a=ip(r,Mr)

            ## BEGIN i=i+1
            x += alpha*d
            r -= alpha*Ad
            Mr = M_inv(r)
            ## END

            beta_b=ip(r,Mr)

            d *= beta_b/beta_a
            d += Mr
            ################ end CG.

            ## keep track of the quadratic model
            model_losses.append(model(x,r=r,damp=True))

            # decide whether to stop CG
            small_res = norm(r)<1e-10
            no_progress = self.progress_heuristic(model_losses)
            obj_has_gone_up_so_stopping = False

            gonna_stop = no_progress or small_res

            # STOP_fn is a function which decides on whether to stop
            # CG. In actuality it's a criterion which, once it starts
            # going up, we stop CG.
            STOP_fn = eval(self.STOP_fn_str, locals())

            # BT_fn is a function which decides on how to backtrack.
            print "Evaluating:", self.BT_fn_str
            BT_fn = eval(self.BT_fn_str, locals())

            # ok: this is when we check how CG is doing.
            # we won't be doing it often since it's expensive.
            if self.backtrack_iter_set(i) or gonna_stop:

                # backtracking: keep track of the value of the
                # backtracking objective
                BT_val = BT_fn(x)
                if BT_val < BT_best: # remember the best one
                    BT_best = BT_val
                    BT_x[:] = x
                    BT_i = i

                # keep track of the stopping heuristic
                stop_val = STOP_fn(x)[-1]

                # stop if stop_val is getting worse
                if stop_val > stop_best*self.cg_stop_thresh_factor:
                    # we allow to stop from the objective gone up only after
                    # a certain number of CG steps. Otherwise we don't.
                    if i >= self.cg_min_cg:
                        obj_has_gone_up_so_stopping = True
                        gonna_stop = True

                # if we're better, remember the best
                if stop_val < stop_best:
                    stop_best = stop_val



                ## that's it, really.
                end_cg = time.time()
                tot_cg_time = end_cg - start_cg
                time_per_cg_iter = tot_cg_time / ((i+1)*len(GN_batches))


                #### DO THE PRINTING SIMULTANEOUSLY. AWESOME.
                # print the guts of the cg run to the detailed file.
                titles = ('i', 'model loss', 'stop loss', 'BT_val',
                          '|x|', '|r|', '|x|_A', 'iter time')

                values = (i, model_losses[-1], stop_val, BT_val,
                          norm(x), norm(r),  np.sqrt(-2*ip(r-b,x)), time_per_cg_iter)

                titles_template = '|' + '|'.join([' %12s ']*len(titles)) + '|' + '\n'
                values_template = '|' + '|'.join([' %12.6f ']*len(values)) + '|' + '\n'

                # print the header at i==0
                if i==0:
                    self.printf('_'*(len(titles_template % titles)-1)+'\n', detail=True)
                    self.printf(titles_template % titles, detail=True)
                self.printf(values_template % values, detail=True)

            # finally: if we're stopping, stop, and explain why (in
            # the log)
            if gonna_stop:
                self.printf('-'*(len(titles_template % titles)-1)+'\n', detail=True)
            if no_progress:
                self.printf('CG: no_progress\n')
            if small_res:
                self.printf('CG: small res\n')
            if obj_has_gone_up_so_stopping:
                self.printf('CG: stopping obj has gone up. Stopping.\n')
            if gonna_stop:
                break

        # this is the new parameter update
        new_x = BT_x
        def calc_rho(obj, model):
            import numpy as np
            if obj > 0:
                return -np.inf
            if model == 0:
                return -np.inf
            return obj/model

        # evaluate the reduction ratio rho using the RHO_nom_str and RHO_denom_str
        RHO_nom = eval(self.RHO_nom_str, locals())[0] # 0 should correspond to l2_loss
        RHO_denom = eval(self.RHO_denom_str, locals())

        # get the roh
        RHO = calc_rho(obj =  RHO_nom,
                       model = RHO_denom)

        self.printf('CG: rho:%12.6f = nom=%12.6f / denom=%12.6f\n'
                    % (RHO, RHO_nom, RHO_denom))
        self.printf('CG: |bt_x|=%12.6f, |x|=%12.6f\n' % (norm(new_x), norm(x)))
        self.printf('BT/CG = %d/%d\n' % (BT_i, i))

        self.rho = RHO
        self._total_num_cg = i

        # but note: self.CG_x is the last solution of CG, which is
        # used to initialize the next run of CG. However, we change
        # the parameters with new_x (aka BT_x), which is different.
        # All of that is described in the original HF paper.

        return new_x


    def line_search(self, v):
        # here we do the line search to make sure that we're doing
        # well on the line_search_batches. It is rarely used, but it
        # helps prevent major mistakes that HF might make.
        def LS_loss(x):
            return self.losses(self.line_search_batches, self.X + x)

        LS_loss_0 = LS_loss(0)

        def LS_red(x):
            return LS_loss(x) - LS_loss_0

        self.printf('line_search: ')
        distances = [.8**i for i in range(50)] + [0]
        assert distances[0]==1

        for i, step in enumerate(distances):
            if i % 6 == 0 and self.consumer.check_stop_message():
                raise ApiStoppedTraining()
            cur_red = LS_red(step*v)
            if cur_red[-1] < 0: # a reduction
                self.X += step*v
                break # so stop.

        self.printf('%s linesearches, step = %4.3f, cur_red=%12.6f\n' % (i, step, cur_red[-1]))

        ## This is a minor precaution which never happens on curves but can
        ## happen on some of the RNNs. Basically, if there was no reduction
        ## in the objective even when the stepsize is truly tiny,
        if step == 0:
            self.printf('line_search: NOTE:setting CG_x to zero because we chose a '
                        'stepsize of 0 for the line_search.\n')
            self.CG_x *= 0

    def cross_validate(self, batches, X):
        # overridden in c3_par_c.py
        pass

    def get_validation_data(self):
        # overloaded in c3_par_c.py
        pass

    def optimize(self, stats_reporter=None, train_pipe_param=None):
        if self.resume_cost:
            self.high_score, self.lower_loss = self.resume_cost
            self.resume_cost = None
        else:
            self.high_score = 0.
            self.lower_loss = None
        time_of_iteration_start = time.time()
        try:
            for self.iter in xrange(self.iter, self.maxnum_iter+1):

                # limiting training batch count per iteration
                per_iteration_count = 5 # batch count per iteration HARDCODED
                batches_count = len(self.train_batches)
                dataset_count = int(batches_count / per_iteration_count)
                trailing_set_size = per_iteration_count
                if batches_count % per_iteration_count != 0:
                    dataset_count = dataset_count + 1
                    trailing_set_size = batches_count % per_iteration_count
                current_set = (self.iter - 1) % dataset_count
                start = per_iteration_count * current_set
                if current_set == dataset_count - 1:
                    stop = start + trailing_set_size
                else:
                    stop = start + per_iteration_count
                print dataset_count, trailing_set_size, start, stop
                self._train_batches = self.train_batches[start:stop]
                self.grad_batches = self._train_batches
                self.GN_batches = self._train_batches
                self.line_search_batches= self._train_batches

                print self.train_batches, self._train_batches, self.test_batches
                print self.grad_batches, self.GN_batches, self.line_search_batches

                if type(self.W) is str:
                    W_arr = self.W.split('\n')
                    v = int(W_arr[1].split('=')[1])
                    h = int(W_arr[2].split('=')[1])
                    f = int(W_arr[3].split('=')[1])
                    o = int(W_arr[4].split('=')[1])

                # for dropout, create a new mask...
                #self.dropout_mask = (g.rand((1, h))>.5)
                if self.save_freq is not None:
                    if self.iter == 2:
                        self.printf('initial saving, to make sure everything works.')


                from ersatz.mrnn.opt.m.rnn.mrnn import MRNN
                mrnn = MRNN(v, h, f, o, None, None, False,
                            number_of_timesteps_to_use=self.number_of_timesteps_to_use)
                mrnn = mrnn.unpack(self.X)

                # update_batches: make sure the data_object produces
                # a fresh batch of data.
                self.update_batches()

                if self.use_dropout:
                    self.refresh_mask() # for dropout

                self.printf('\n\n\nHF: iter = %s\n' % self.iter)
                grad, grad2, train_losses = self.grad(self.grad_batches, self.X)

                if self.iter % self.test_freq == 0:
                    self.test_losses = \
                        self.losses(self.test_batches, self.X)
                else:
                    from ersatz.mrnn.opt.utils.extra import random_subset_2
                    cheap_test_batches = random_subset_2(self.test_batches, self.test_otherwise_on_num)
                    self.cheap_test_losses = self.losses(cheap_test_batches, self.X)

                accuracy_for_each_timestep_test, \
                total_accuracy_test, \
                accuracy_for_last_10_steps_test, \
                confusion_test = self.get_accuracy(self.test_batches, self.X)

                accuracy_for_each_timestep_train, \
                total_accuracy_train, \
                accuracy_for_last_10_steps_train, \
                confusion_train = self.get_accuracy(self._train_batches, self.X)

                # should probably add validation batches here too...

                model_data = {}
                if total_accuracy_test > self.high_score:
                    # we only want to save if it is a better model than the last save
                    # according to our validation set
                    # this check should be done before an HF iteration, but never on the
                    # first run after a refresh...
                    # Also, don't save it if it's early in the number of iterations, like first 10
                    print colored('new score reached','green')
                    self.high_score = copy.copy(total_accuracy_test)
                    self.lower_loss = self.test_losses.mean()
                    self.save('best')

                model_data = self.save('latest')

                accuracy_for_each_timestep_train = [[x for x in accuracy_for_each_timestep_train]]
                accuracy_for_each_timestep_test = [[x for x in accuracy_for_each_timestep_test]]
                time_of_iteration_end = time.time()
                iteration_stats = {
                                    'iteration': self.iter,
                                    'grad1': norm(grad),
                                    'grad2': norm(grad2),
                                    'train_loss': train_losses.mean(),
                                    'train_accuracy': total_accuracy_train,
                                    'train_last_10_steps_acc': np.mean(accuracy_for_last_10_steps_train),
                                    'train_accuracy_matrix': accuracy_for_each_timestep_train,
                                    'test_loss': self.test_losses.mean(),
                                    'test_accuracy': total_accuracy_test,
                                    'test_last_10_steps_acc': np.mean(accuracy_for_last_10_steps_test),
                                    'test_accuracy_matrix': accuracy_for_each_timestep_test,
                                    'lambda': self.damping[0],
                                    'mu': self.damping[1],
                                    'time': time_of_iteration_end - time_of_iteration_start,
                                    'confusion_matrix': confusion_test,
                                    'confusion_matrix_train': confusion_train
                                    }
                if hasattr(self, 'rho'):
                    iteration_stats.update({'total_num_cg': self._total_num_cg,
                        'norm_CG_x': norm(self.CG_x), 'rho': self.rho})

                nm = mrnn.unpack(self.X)
                iteration_stats.update({
                        '1_h_norm': norm(nm.h_init), 'h_f_norm': norm(nm.W_hf),
                        'f_h_norm': norm(nm.W_fh), '1_f_norm': norm(nm.f_bias),
                        'v_h_norm': norm(nm.W_vh), 'v_f_norm': norm(nm.W_vf),
                        'h_o_norm': norm(nm.W_ho)
                        })

                if self.is_model_resumed:
                    self.is_model_resumed = False
                else:
                    api_response = self.report_stat(iteration_stats,
                                                    model_data,
                                                    stats_reporter)

                    #if response False, it's api error or job canceled, stop optimizing
                    if not api_response:
                        raise Exception('Api respond with not 200 status, stop optimizing')


                self.printf('HF: |grad|  =%8.5f\n' % norm(grad))
                self.printf('HF: |grad2| =%8.5f\n' % norm(grad2))
                self.printf('HF: |self.X|=%8.5f\n' % norm(self.X))
                self.printf('HF: train    = %s\n'   % train_losses)
                self.printf('HF: train_t_acc = %s%%\n'   % total_accuracy_train)
                self.printf('HF: train_l10_acc  = %s%%\n'   % accuracy_for_last_10_steps_train)
                self.printf('HF: train_step_acc =\n%s\n'   % accuracy_for_each_timestep_train)
                self.printf('HF: test     = %s\n'   % self.test_losses)
                self.printf('HF: test_t_acc = %s%%\n'   % total_accuracy_test)
                self.printf('HF: test_l10_acc  = %s%%\n'   % accuracy_for_last_10_steps_test)
                self.printf('HF: test_step_acc =  \n%s\n'   % accuracy_for_each_timestep_test)
                self.printf('HF: cheaptest= %s\n'   % self.cheap_test_losses)
                self.printf('HF: overfit  = %s\n'   % (self.test_losses - train_losses))
                self.printf('HF: damping =  %s\n' % self.damping)

                #end of iteration
                if self.iter == self.maxnum_iter:
                    #don't calc if it was last iter
                    continue

                print "1111111111111111"

                time_of_iteration_start = time.time()
                new_direction = self.get_new_direction(grad, grad2)

                print "2222222222222222"

                self.damping = self.damping_heuristic(
                    self.damping, self.rho, self.max_damping,
                    self.behavior_at_max_damping)

                self.line_search(new_direction)

                self.CG_x *= self.cg_shrink_factor

                self.printf('HF: tot_batch = %s; num_cg = %s.\n'
                       % (self._total_batch, self._total_num_cg))


                if self.iter % 10 == 0:
                    self.print_dna()


                if self._total_num_cg > self.maxnum_cg:
                    break

                if self.iter is not 0 and self.iter % self.rotate_data_after == 0:
                    self.printf('*** Cycling data ***\n')
                    self.cycle_data()


        except KeyboardInterrupt:
            self.printf('Ctrl-C: stopping.\n')
            print 'Ctrl-C: stopping.\n'
        except UnstableModelException as e:
            print colored('***************************************', 'red')
            print colored('***  model became numerically unstable, returning last iter high score')
            print colored('***************************************', 'red')
            raise e
        except ApiStoppedTraining:
            print colored('***************************************', 'blue')
            print colored('***  STOP signal, waiting for commands')
            print colored('***************************************', 'blue')
            raise ApiStoppedTraining()
        except Exception as e:
            print colored('***************************************', 'red')
            print colored('***  %s' % e, 'red')
            print colored('***  %s' % traceback.print_tb(sys.exc_info()[2]), 'red')
            print colored('***************************************', 'red')
            raise e
        finally:
            self.shutdown_workers()


        if self.high_score > 0.:
            #return self.high_score
            return self.lower_loss, self.high_score
        else:
            raise Exception('the high score is not done right')



    def print_dna(self):
                    self.printf('\nThe report:\n')
                    self.printf('\n%s\n' % self.message)
                    exprs = ['self.batch_fn',
                             'self.W',
                             'self.init_damping',
                             'len(self.train_batches)',
                             'len(self.test_batches)',
                             'len(self.grad_batches)',
                             'len(self.GN_batches)',
                             'len(self.line_search_batches)',
                             'self.backtrack_iter_set',
                             'self.BT_fn_str',
                             'self.STOP_fn_str',
                             'self.RHO_nom_str',
                             'self.RHO_denom_str',
                             'self.cg_max_cg',
                             'self.cg_min_cg',
                             'self.cg_shrink_factor',
                             'self.cg_precond_expr',
                             'self.cg_damper_expr',
                             'self.maxnum_iter',
                             'self.high_score',
                             '1',
                             'self.cg_stop_thresh_factor']

                    for e in exprs:
                        a = eval(e, dict(self=self))
                        self.printf('%s = %s\n' % (e, a))
                    self.printf('HF: end printing of stats.\n')




    def save(self, tag='latest'):
        self.printf('saving...\n')

        # try getting the network size back from string
        # see MRNN.__repr__() in mrnn.py
        # and info_provider() in c3_par_c.py
        if type(self.W) is str:
            W_arr = self.W.split('\n')
            v = int(W_arr[1].split('=')[1])
            h = int(W_arr[2].split('=')[1])
            f = int(W_arr[3].split('=')[1])
            o = int(W_arr[4].split('=')[1])
        else:
            v = self.W.v
            h = self.W.h
            f = self.W.f
            o = self.W.o

        data = dict(X = self.X.asarray(),
                  iter = self.iter,
                  CG_x = self.CG_x.asarray(),
                  damping = self.damping,
                  _total_num_cg = self._total_num_cg,
                  v = v,
                  h = h,
                  f = f,
                  o = o)
        path = os.path.join(conf.settings.WORKING_DIR,
                            'models/' + self.path.replace('.','/'),
                            tag + '.X')
        with open(path, 'w') as f:
            pickle.dump(data, f)
        self.printf('done saving.\n')
        return data

    def report_stat(self, stats, model_data, stats_reporter):
        modeldata_key = aws.save_modeldata(self.model_id, stats['iteration'], model_data)
        payload = {
            'model': self.model_id,
            'data': stats,
            's3_data': modeldata_key,
            'queue_key': self.queue_key
        }

        # publish stats
        if stats_reporter:
            stats_reporter(json.dumps(payload, cls=NPArrayEncoder))

        return api.post('/api/stats/', payload)


    def load(self, path=None, s3_data=None, high_score=None, lower_loss=None):
        # prefix = self.path + '.X.'

        # import os
        # files = os.listdir('.')

        # candidates = [f
        #               for f in files
        #               if f.startswith(prefix)]

        # iter_nums = [int(f[len(prefix):])
        #              for f in candidatest]


        # biggest_int = max(iter_nums)

        # path = prefix + str(biggest_int)

        if s3_data:
            data = json.loads(aws.get_data(s3_data))
        else:
            if path is None:
                path = self.path + '.X'
            print "Loading network state from", path
            with open(path, 'r') as f:
                data = pickle.load(f)

        if high_score and lower_loss:
            self.resume_cost = [high_score, lower_loss]
        self.X[:] = data['X']
        self.CG_x[:] = data['CG_x']
        if not self.settings.lambda_override:
            self.damping[:] = data['damping']
        self.iter = data['iter']
        self._total_num_cg = data['_total_num_cg']
        self.is_model_resumed = True
        print "Loaded"
