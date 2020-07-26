# This file is part of QuTiP: Quantum Toolbox in Python.
#
#    Copyright (c) 2011 and later, Paul D. Nation and Robert J. Johansson.
#    All rights reserved.
#
#    Redistribution and use in source and binary forms, with or without
#    modification, are permitted provided that the following conditions are
#    met:
#
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#    3. Neither the name of the QuTiP: Quantum Toolbox in Python nor the names
#       of its contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
#    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#    "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#    LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
#    PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#    HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#    SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#    LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#    DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#    THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#    OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
###############################################################################

import numpy as np
from numpy.random import rand
import scipy.linalg as la
from numpy.testing import assert_, assert_equal, run_module_suite
import scipy

from qutip import (
    rand_dm, rand_unitary, spre, spost, vector_to_operator, operator_to_vector,
    stack_columns, unstack_columns, unstacked_index, stacked_index, tensor,
    sprepost, to_super, identity, destroy, create, qeye, QobjEvo, Qobj,
    liouvillian, lindblad_dissipator,
)
from qutip.core.permute import reshuffle
from qutip.core import data as _data


def f(t, args):
    return t*(1-0.5j)


def liouvillian_ref(H, c_ops=[]):
    L = -1.0j * (spre(H) - spost(H)) if H else 0
    for c in c_ops:
        if c.issuper:
            L += c
        else:
            cdc = c.dag() * c
            L += spre(c)*spost(c.dag()) - 0.5*spre(cdc) - 0.5*spost(cdc)
    return L


class TestMatVec:
    """
    A test class for the QuTiP function for matrix/vector conversion.
    """

    def testOperatorVector(self):
        """
        Superoperator: Operator - vector - operator conversion.
        """
        N = 3
        rho1 = rand_dm(N)
        rho2 = vector_to_operator(operator_to_vector(rho1))

        assert_((rho1 - rho2).norm() < 1e-8)

    def testOperatorVectorTensor(self):
        """
        Superoperator: Operator - vector - operator conversion with a tensor product state.
        """
        Na = 3
        Nb = 2
        rhoa = rand_dm(Na)
        rhob = rand_dm(Nb)
        rho1 = tensor(rhoa, rhob)
        rho2 = vector_to_operator(operator_to_vector(rho1))

        assert_((rho1 - rho2).norm() < 1e-8)

    def testOperatorVectorNotSquare(self):
        """
        Superoperator: Operator - vector - operator conversion for non-square matrix.
        """
        op1 = Qobj(np.random.rand(6).reshape((3, 2)))
        op2 = vector_to_operator(operator_to_vector(op1))

        assert_((op1 - op2).norm() < 1e-8)

    def testOperatorSpreAppl(self):
        """
        Superoperator: apply operator and superoperator from left (spre)
        """
        N = 3
        rho = rand_dm(N)
        U = rand_unitary(N)

        rho1 = U * rho
        rho2_vec = spre(U) * operator_to_vector(rho)
        rho2 = vector_to_operator(rho2_vec)

        assert_((rho1 - rho2).norm() < 1e-8)

    def testOperatorSpostAppl(self):
        """
        Superoperator: apply operator and superoperator from right (spost)
        """
        N = 3
        rho = rand_dm(N)
        U = rand_unitary(N)

        rho1 = rho * U
        rho2_vec = spost(U) * operator_to_vector(rho)
        rho2 = vector_to_operator(rho2_vec)

        assert_((rho1 - rho2).norm() < 1e-8)

    def testOperatorUnitaryTransform(self):
        """
        Superoperator: Unitary transformation with operators and superoperators
        """
        N = 3
        rho = rand_dm(N)
        U = rand_unitary(N)

        rho1 = U * rho * U.dag()
        rho2_vec = spre(U) * spost(U.dag()) * operator_to_vector(rho)
        rho2 = vector_to_operator(rho2_vec)

        assert_((rho1 - rho2).norm() < 1e-8)

    def testMatrixVecMat(self):
        """
        Superoperator: Conversion matrix to vector to matrix
        """
        M = _data.csr.CSR(scipy.sparse.csr_matrix(rand(10, 10)))
        V = stack_columns(M)
        M2 = unstack_columns(V)
        assert_(_data.csr.nnz(M - M2) == 0)

    def testVecMatVec(self):
        """
        Superoperator: Conversion vector to matrix to vector
        """
        V = _data.csr.CSR(scipy.sparse.csr_matrix(rand(100)[:, None]))
        M = unstack_columns(V)
        V2 = stack_columns(M)
        assert_(_data.csr.nnz(V - V2) == 0)

    def testVecMatIndexConversion(self):
        """
        Superoperator: Conversion between matrix and vector indices
        """
        N = 10
        for I in range(N * N):
            i, j = unstacked_index(N, I)
            I2 = stacked_index(N, i, j)
            assert I == I2

    def testVecMatIndexCompability(self):
        """
        Superoperator: Compatibility between matrix/vector and
        corresponding index conversions.
        """
        N = 10
        M = _data.create(rand(N, N))
        V = stack_columns(M)
        for I in range(N * N):
            i, j = unstacked_index(N, I)
            assert V.to_array()[I, 0] == M.to_array()[i, j]

    def test_reshuffle(self):
        U1 = rand_unitary(2)
        U2 = rand_unitary(3)
        U3 = rand_unitary(4)

        U = tensor(U1, U2, U3)
        S = to_super(U)
        S_col = reshuffle(S)

        assert_equal(S_col.dims[0], [[2, 2], [3, 3], [4, 4]])

        assert_(reshuffle(S_col) == S)

    def test_sprepost(self):
        U1 = rand_unitary(3)
        U2 = rand_unitary(3)

        S1 = spre(U1) * spost(U2)
        S2 = sprepost(U1, U2)

        assert_(S1 == S2)

    def testLiouvillianImplem(self):
        """
        Superoperator: Randomized comparison of standard and reference
        Liouvillian functions.
        """
        N1 = 3
        N2 = 4
        N3 = 5

        a1 = tensor(rand_dm(N1, density=0.75), identity(N2), identity(N3))
        a2 = tensor(identity(N1), rand_dm(N2, density=0.75), identity(N3))
        a3 = tensor(identity(N1), identity(N2), rand_dm(N3, density=0.75))
        H = a1.dag() * a1 + a2.dag() * a2 + a3.dag() * a3

        c_ops = [np.sqrt(0.01) * a1, np.sqrt(0.025) * a2, np.sqrt(0.05) * a3]

        L1 = liouvillian(H, c_ops)
        L2 = liouvillian_ref(H, c_ops)

        assert_((L1 - L2).norm('max') < 1e-8)



class TestSuper_td:
    """
    A test class for the QuTiP superoperator functions.
    """
    N = 3
    t1 = QobjEvo([qeye(N)*(1.+0.1j),[create(N)*(1.-0.1j),f]])
    t2 = QobjEvo([destroy(N)*(1.-0.2j)])
    t3 = QobjEvo([[destroy(N)*create(N)*(1.+0.2j),f]])
    q1 = qeye(N)*(1.+0.3j)
    q2 = destroy(N)*(1.-0.3j)
    q3 = destroy(N)*create(N)*(1.+0.4j)

    def test_spre_td(self):
        "Superoperator: spre, time-dependent"
        assert_(spre(self.t1)(.5) == spre(self.t1(.5)))

    def test_spost_td(self):
        "Superoperator: spre, time-dependent"
        assert_(spost(self.t1)(.5) == spost(self.t1(.5)))

    def test_sprepost_td(self):
        "Superoperator: sprepost, time-dependent"
        # left QobjEvo
        assert_(sprepost(self.t1, self.q2)(.5) ==
                sprepost(self.t1(.5), self.q2))
        # left QobjEvo
        assert_(sprepost(self.q2, self.t1)(.5) ==
                sprepost(self.q2, self.t1(.5)))
        # left 2 QobjEvo, one cte
        assert_(sprepost(self.t1, self.t2)(.5) ==
                sprepost(self.t1(.5), self.t2(.5)))

    def test_operator_vector_td(self):
        "Superoperator: operator_to_vector, time-dependent"
        assert_(operator_to_vector(self.t1)(.5) ==
                operator_to_vector(self.t1(.5)))
        vec = operator_to_vector(self.t1)
        assert_(vector_to_operator(vec)(.5) == vector_to_operator(vec(.5)))

    def test_liouvillian_td(self):
        "Superoperator: liouvillian, time-dependent"
        assert_(liouvillian(self.t1)(0.5) == liouvillian(self.t1(0.5)))
        assert_(liouvillian(None, [self.t2])(0.5) ==
                liouvillian(None, [self.t2(0.5)]))
        assert_(liouvillian(self.t1, [self.t2, self.q1, self.t3],
                            chi=[1,2,3])(0.5) ==
                liouvillian(self.t1(0.5), [self.t2(0.5), self.q1, self.t3(0.5)],
                            chi=[1,2,3]))

    def test_lindblad_dissipator_td(self):
        "Superoperator: lindblad_dissipator, time-dependent"
        assert_(lindblad_dissipator(self.t2)(.5) ==
                lindblad_dissipator(self.t2(.5)))
        assert_(lindblad_dissipator(self.t2, self.q1)(.5) ==
                lindblad_dissipator(self.t2(.5), self.q1))
        assert_(lindblad_dissipator(self.q1, self.t2)(.5) ==
                lindblad_dissipator(self.q1, self.t2(.5)))



if __name__ == "__main__":
    run_module_suite()
