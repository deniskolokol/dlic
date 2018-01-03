import re
from collections import Counter
import numpy as np
from ersatz.mrnn import gnumpy as g
from ersatz.mrnn.util import to_masked_array_of_different_len as to_masked
from ersatz.mrnn.opt.utils import nonlin
from ersatz.mrnn.opt.utils.extra import unpack, sparsify_strict

# MRNN. The MRNN is cool. We define it here.
class MRNN(object):
    def __init__(self,
                 # give it what it needs: sizes etc
                 v, h, f, o,

                 hid_nonlin, # the nonlinearities

                 out_nonlin, # the output nonlinearity

                 struct_damp_nonlin=nonlin.Tanh, # the structural damping nonlinearity

                 init=True, number_of_timesteps_to_use=99999999):
        """
        v int number of features
        h int number of hidden units
        f int number of factored units
        o int
        hid_nonlin function hidden layer nonlinearity function
        out_nonlin function output nonlinearity function
        struct_damp_nonlin function
        init bool whether to initialize arrays to random data
        """
        self.v = v
        self.h = h
        self.f = f
        self.o = o

        self.hid_nonlin = hid_nonlin
        self.out_nonlin = out_nonlin
        self.struct_damp_nonlin = struct_damp_nonlin

        self.number_of_timesteps_to_use = number_of_timesteps_to_use

        if init:
            self.h_init = g.randn(1, h)
            self.W_hf = g.randn(h, f)
            self.W_fh = g.randn(f, h)
            #self.W_hh = g.randn(h, h)
            self.f_bias = g.zeros((1, f))

            self.W_vh = g.randn(v, h)
            self.W_vf = g.randn(v, f)
            self.W_ho = g.randn(h, o)


        if hid_nonlin is None:
            hid_nonlin = nonlin.Tanh
        self.hid_nonlin = hid_nonlin

        if out_nonlin is None:
            out_nonlin = nonlin.Lin

        self.out_nonlin = out_nonlin



    def initialize_self(self, num_in, scale_big, scale_small=0.,
                        vars_to_exclude=[], vars=None):

        # the initialization routine
        for (var_name, var) in self.__dict__.iteritems():

            if (var_name not in vars_to_exclude and
                isinstance(var, g.garray)     and
                ((vars is None) or (var_name in vars))):
                    sparsify_strict(var, num_in, scale_big, scale_small)
                    print('MRNN:sparsifying %s\n' % var_name)

        return self

    def pack(self):
        return g.concatenate([self.h_init.ravel(),
                              self.W_hf.ravel(),
                              self.W_fh.ravel(),
                              #self.W_hh.ravel(),
                              self.f_bias.ravel(),
                              self.W_vh.ravel(),
                              self.W_vf.ravel(),
                              self.W_ho.ravel()])

    def unpack(self, X):
        ans = MRNN(self.v, self.h, self.f, self.o,
                   self.hid_nonlin, self.out_nonlin,
                   number_of_timesteps_to_use=self.number_of_timesteps_to_use)

        (ans.h_init,
         ans.W_hf,
         ans.W_fh,
         #ans.W_hh,
         ans.f_bias,
         ans.W_vh,
         ans.W_vf,
         ans.W_ho) = unpack([self.h_init,
                             self.W_hf,
                             self.W_fh,
                             #self.W_hh,
                             self.f_bias,
                             self.W_vh,
                             self.W_vf,
                             self.W_ho],
                            X)
        return ans

    def forward_pass(self, batch, O=None, mask=None):
        # the forward pass: compute the state. it's the most important
        # function and everything else is defined in terms of it.

        if len(batch)==2 and type(batch)==tuple:
            V,O=batch
            assert len(V)==len(O)
        elif len(batch)==3 and type(batch)==tuple:
            V,O,M=batch
            assert len(V)==len(O)==len(M)
        else:
            V=batch

        if V[0] is not None:
            V = [None] + V

        T = len(V)-1
        batch_size = V[1].shape[0]

        A, B, H, OX = [[None]*(T+1) for _ in range(4)]

        H[0] = g.tile(self.h_init, (batch_size, 1))
        for t in range(1, T+1):
            batch_size = V[t].shape[0]
            B[t] = g.dot(V[t],   self.W_vf).tanh()
            A[t] = g.dot(H[t-1], self.W_hf)[:batch_size, :]
            C_t = g.dot(V[t], self.W_vh) # + hh stuff

            AB = A[t]*(B[t] + self.f_bias)

            HX_t = g.dot(AB, self.W_fh) + C_t
            H[t] = self.hid_nonlin(HX_t)

            #next line implements dropout
            if type(mask) is str and mask=='validate':
                # when you actually use your model, you use all the
                # hidden units and halve their outgoing weights
                #
                #H[t] = H[t]
                new_w_ho = self.W_ho * .5
            elif mask is not None:
                H[t] = H[t]*g.tile(mask, (H[t].shape[0], 1))
                new_w_ho = self.W_ho * g.tile(mask, (self.W_ho.shape[1], 1)).transpose()
            else:
                new_w_ho = self.W_ho

            OX[t] = g.dot(H[t], new_w_ho)

        return (V[1:], A, B, H, OX[1:])

    def R_forward_pass(self, state, R):
        # differentiate the forward pass using the R-op.
        # R is the direciton of our direcitonal derivative.
        # Really simple stuff.

        V, A, B, H, OX = state
        if V[0] is not None:
            V = [None] + V
#         if A[0] is not None:
#             A = [None] + A
#         if B[0] is not None:
#             B = [None] + B
#         if H[0] is not None:
#             H = [None] + H
        if OX[0] is not None:
            OX = [None] + OX




        T = len(V)-1
        batch_size = V[1].shape[0]
        R_OX, R_HX = [None]*(T+1), [None]*(T+1)

        R_H_t = g.tile(R.h_init, (batch_size, 1))
        for t in range(1, T+1):
            batch_size = V[t].shape[0]
            R_H_1t = R_H_t

            R_B_t = g.dot(V[t], R.W_vf) * (1-B[t]*B[t])
            R_A_t = g.dot(R_H_1t, self.W_hf) + g.dot(H[t-1], R.W_hf)
            R_C_t = g.dot(V[t], R.W_vh) # + hh stuff

            B_t_f = B[t] + self.f_bias
            AB = A[t]*B_t_f
            R_AB = R_A_t[:batch_size,:]*B_t_f + A[t]*(R_B_t + R.f_bias)

            R_HX[t] = g.dot(R_AB, self.W_fh) + g.dot(AB, R.W_fh) + R_C_t
            R_H_t = self.hid_nonlin.grad_y(H[t]) * R_HX[t]

            R_OX[t] = g.dot(H[t], R.W_ho) + g.dot(R_H_t, self.W_ho)

        return (R_HX, R_OX[1:])

    def backward_pass(self, state, dOX, R_state=None, mu=0., compute_grad2=False):
        # backprop.

        if R_state is None:
            R_HX, R_OX = None, None
        else:
            R_HX, R_OX = R_state

        V, A, B, H, OX = state
        if V[0] is not None:
            V = [None] + V
#         if A[0] is not None:
#             A = [None] + A
#         if B[0] is not None:
#             B = [None] + B
#         if H[0] is not None:
#             H = [None] + H
        if OX[0] is not None:
            OX = [None] + OX
        if dOX[0] is not None:
            dOX = [None] + dOX


        T = len(V)-1

        grad = self.unpack(self.pack() * 0)
        if compute_grad2:
            grad2 = self.unpack(self.pack() * 0)
        else:
            grad2 = None


        dH_1t = g.zeros(H[T].shape)
        prev_batch_size = H[T].shape[0]
        for t in reversed(range(1, T+1)):

            dH_t = g.dot(dOX[t], self.W_ho.T)
            dH_t[:prev_batch_size, :] += dH_1t

            grad.W_ho += g.dot(H[t].T, dOX[t])
            if compute_grad2:
                grad2.W_ho += g.dot((H[t]*H[t]).T, dOX[t]*dOX[t])

            ## backpropagate the nonlinearity: at this point, dHX_t, the gradinet
            ## wrt the total inputs to H_t, is correct.
            dHX_t = dH_t * self.hid_nonlin.grad_y(H[t])

            ## Add the structured reg at this point: That's good.
            if R_HX is not None:
                dHX_t += float(mu) * self.struct_damp_nonlin.H_prod(R_HX[t], H[t], M = 1)


            ## had hh grad here: (H[t-1], dHX_t)

            B_t_f = (B[t] + self.f_bias)
            AB = A[t]*B_t_f

            grad.W_fh += g.dot(AB.T, dHX_t)
            grad.W_vh += g.dot(V[t].T, dHX_t)
            if compute_grad2:
                _dHX2 = dHX_t*dHX_t
                grad2.W_fh += g.dot((AB*AB).T, _dHX2)
                grad2.W_vh += g.dot((V[t]*V[t]).T, _dHX2)


            ## do the intermediate backprop:
            dAB = g.dot(dHX_t, self.W_fh.T)


            dB = dAB*A[t]

            grad.f_bias += dB.sum(0)
            dBB = dB * (1-B[t]*B[t])
            grad.W_vf += g.dot(V[t].T, dBB)

            dA = dAB * B_t_f
            Ht_minus_one = H[t-1][:dA.shape[0], :]
            grad.W_hf += g.dot(Ht_minus_one.T, dA)

            if compute_grad2:
                grad2.f_bias += (dB*dB).sum(0)
                grad2.W_vf += g.dot((V[t]*V[t]).T, dBB*dBB)
                grad2.W_hf += g.dot((Ht_minus_one*Ht_minus_one).T, dA*dA)

            dH_1t = g.dot(dA, self.W_hf.T)
            prev_batch_size = V[t].shape[0]


        grad.h_init += dH_1t.sum(0)
        if compute_grad2:
            grad2.h_init += (dH_1t*dH_1t).sum(0)

        return grad, grad2

    def loss(self, (V, O, M), mask=None):
        assert len(V) == len(O) == len(M)

        (V, A, B, H, OX) = self.cur_state_from_loss = self.forward_pass(V, mask=mask)

        loss = 0.
        for t in range(len(O)):
            loss +=  self.out_nonlin.loss(OX[t], O[t], M[t])

#        print "Final time step loss"
        # sigmoid activation
#        print ((O[-1]*g.log_1_sum_exp(-OX[-1]) + (1-O[-1])*g.log_1_sum_exp(OX[-1]))*M[-1])

        return loss


    def preds(self, V, mask):
        (V, A, B, H, OX) = self.forward_pass(V, mask=mask)
        assert len(OX)==len(H)-1
        return OX

    def grad(self, (V, O, M), loss=False, compute_grad2=False, mask=None):

        state = self.forward_pass(V, mask=mask)

        OX = state[-1]

        dOX = [None] * len(OX)

        loss = 0.
        #accuracy = []
        for t in range(len(O)):
            #if t == len(O) - 1:
                #import rdb; rdb.set_trace() ### XXX BREAKPOINT
            #accuracy.append( (self.out_nonlin(OX[t]).argmax(axis=1) == O[t].argmax(axis=1)).astype(float) )
            dOX[t] = self.out_nonlin.grad(OX[t], O[t], M[t])
            loss += self.out_nonlin.loss(OX[t], O[t], M[t])


        grad, grad2 = self.backward_pass(state, dOX, compute_grad2 = compute_grad2)

        return grad, grad2, loss

    def get_accuracy(self, (V, O, M)):
        state = self.forward_pass(V)
        OX = state[-1]

        accuracy = []
        confusion = {}
        weights = []
        is_linear_nonlin = re.search('The Linear Nonlinearity', str(self.out_nonlin))
        if not is_linear_nonlin:
            for i in range(len(O[0][0])):
                confusion[i] = Counter()
        for t in range(len(O)):
            actual = O[t].argmax(axis=1)
            predicted = self.out_nonlin(OX[t]).argmax(axis=1)
            accuracy.append((actual == predicted).astype(float))
            klasses = np.unique(actual)
            if not is_linear_nonlin:
                for klass in klasses:
                    confusion[klass].update(predicted[actual==klass].tolist())
            weights.append(O[t].shape[0])
        weights = np.array(weights)
        accuracy = to_masked(accuracy)
        accuracy_for_each_ts = accuracy.mean(axis=1)

        return accuracy_for_each_ts, confusion, weights

    def gauss_newton(self, data, R, state=None, mu=0., mask=None):
        (V, O, M) = data

        if state is None:
            state = self.forward_pass(V, mask=mask)
        (V, A, B, H, OX) = state

        (R_HX, R_OX) = R_state = self.R_forward_pass(state, R)

        LJ = [None] * len(R_OX)
        for t in range(len(OX)):
            P_t = self.out_nonlin(OX[t])
            LJ[t] = self.out_nonlin.H_prod(R_OX[t], P_t, M[t])

        ans, ans2 = self.backward_pass(state, LJ, R_state, mu=mu)
        return ans

    def __repr__(self):
        return '\n'.join(['MRNN:',
                          'v = %s' % self.v,
                          'h = %s' % self.h,
                          'f = %s' % self.f,
                          'o = %s' % self.o])
