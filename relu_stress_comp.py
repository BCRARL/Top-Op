import numpy as np
from fenics import *
import ufl as ufl
from ufl import nabla_div
from fenics_adjoint import *
from pyadjoint import ipopt

# turn off redundant output in parallel
parameters["std_out_all_processes"] = False

L = 2.0                                         # Length
W = 1.0                                         # Width
p = Constant(5.0)                               # Penalization Factor for SIMP
p_norm = 1.0                                    # Normalization Parameter
pa = 5                                          # pnorm order for extension constraint
q = 0.5                                         # Penalization for Stress
eps = Constant(1.0e-3)                          # Epsilon value for SIMP to remove singularities
E = Constant(2.0e+11)                           # Young Modulus
nu = Constant(0.3)                              # Poisson's Ratio
lmbda = (E*nu) / ((1.0 + nu)*(1.0 - (2.0*nu)))  # Lame's first parameter
G = E / (2.0*(1.0 + nu))                        # Lame's second parameter / Shear Modulus
nelx = 100                                      # Number of elements in x-direction
nely = 50                                       # Number of elements in y-direction
C_max = Constant(50000.0)                       # Max Compliance
S_max = Constant(5.0e+8)                        # Max Stress
r = Constant(0.025)                             # Length Parameter for Helmholtz Filter

# Define Mesh
mesh = RectangleMesh(Point(0.0, 0.0), Point(L, W), nelx, nely)
Coordinates = mesh.coordinates()

# Define Function Spaces
U = VectorFunctionSpace(mesh, "Lagrange", 1) # Displacement Function Space
X = FunctionSpace(mesh, "Lagrange", 1)       # Density Function Space

# SIMP Function for Intermediate Density Penalization
def simp(x):
    return eps + (1 - eps) * x**p

# Calculate Strain from Displacements u
def strain(u):
    return 0.5*(nabla_grad(u) + nabla_grad(u).T)

# Calculate Stress from Displacements u
def sigma(u):
    return lmbda*nabla_div(u)*Identity(2) + 2*G*strain(u)

# Calculate Von Mises Stress from Displacements u
def von_mises(u):
    s = sigma(u) - (1./3)*tr(sigma(u))*Identity(2)  # deviatoric stress
    return sqrt(3./2*inner(s, s))

# RELU Function for Global Stress Constraint Computation
def relu(x):
    return (x * (ufl.sign(x) + 1) * 0.5) # ** 2

# Volumetric Load
q = 5000000.0
f = Constant((0.0, q))

# Dirichlet BC em x[0] = 0
def Left_boundary(x, on_boundary):
    return on_boundary and abs(x[0]) < DOLFIN_EPS
u_L = Constant((0.0, 0.0))

bc = DirichletBC(U, u_L, Left_boundary)

# Helmholtz Filter for Design Variables. Helps remove checkerboarding and introduces mesh independency.
# Taken from work done by de Souza et al. (2020)
def helmholtz_filter(rho_n):
      V = rho_n.function_space()

      rho = TrialFunction(V)
      w = TestFunction(V)

      a = (r**2)*inner(grad(rho), grad(w))*dx + rho*w*dx
      L = rho_n*w*dx

      A, b = assemble_system(a, L)
      rho = Function(V)
      solve(A, rho.vector(), b)

      return rho

# Forward problem solution. Solves for displacement u given density x.
def forward(x):
    rho = helmholtz_filter(x)
    u = TrialFunction(U)  # Trial Function
    v = TestFunction(U)   # Test Function
    a = simp(rho)*inner(sigma(u), strain(v))*dx
    L = dot(f, v)*dx
    u = Function(U)
    solve(a == L, u, bc)
    return u  

# MAIN
if __name__ == "__main__":
    x = interpolate(Constant(0.5), X)  # Initial value of 0.5 for each element's density
    u = forward(x)                     # Forward problem

    J = assemble(x*dx)# + (alpha*(x*(1-x)*dx)))# + Constant(1.0e-4)*dot(grad(x),grad(x))*dx)
    m = Control(x)  # Control
    Jhat = ReducedFunctional(J, m)#, derivative_cb_post=eval_cb)  # Reduced Functional

    lb = 0.0  # Inferior
    ub = 1.0  # Superior
    # Class for Enforcing Stress Constraint
    class StressConstraint(InequalityConstraint):
        def __init__(self, S):
            self.S  = S# float(S)
            self.temp_x = Function(X)
            # self.u = interpolate(u, U)

        def function(self, m):
            self.temp_x.vector()[:] = m
            print("Current control vector (density): ", self.temp_x.vector()[:])
            s_current = assemble(relu((von_mises(Control(u).tape_value())*(Control(x).tape_value()**0.5))-self.S)**2*dx)
            if MPI.rank(MPI.comm_world) == 0:
                print("Current stress: ", s_current)

            return [-s_current]

        def jacobian(self, m):
            self.temp_x.vector()[:] = m
            J_stress = assemble(relu((von_mises(u)*(x**0.5))-self.S)**2*dx)
            m_stress = Control(x)
            dJ_stress = compute_gradient(J_stress, m_stress)
            
            return [-dJ_stress.vector()]

        def output_workspace(self):
            return [0.0]

        def length(self):
            """Return the number of components in the constraint vector (here, one)."""
            return 1  

    class ExtensionConstraint(InequalityConstraint):
        "Ensure there is some mass above 1 over all points with x coordinate L"
        def function(self, m):
            a = 0.0
            for (Index, Coordinate) in zip(range(len(m)), Coordinates):
                if Coordinate[0 == L:
                    a += m[Index]**pa
            return [a-1]

        def jacobian(self, m):
            a = m.copy()
            for (Index, Coordinate) in zip(range(len(m)), Coordinates):
                if Coordinate[0]== L:
                    a[Index] = a[Index]**(pa-1)*pa
                else:
                    a[Index] = 0.0
            
            return [a]

        def length(self):
            return 1
        def output_workspace(self):
            return [0.0]
            
    # Class for Enforcing Compliance Constraint
    class ComplianceConstraint(InequalityConstraint):
        def __init__(self, C):
            self.C  = float(C)
            self.tmpvec = Function(X)
            self.u = interpolate(u, U)

        def function(self, m):
            self.tmpvec.vector()[:]=m
            print("Current control vector (density): ", self.tmpvec.vector()[:])
            self.u = forward(self.tmpvec)
            print("Current u vector: ", self.u.vector()[:])
            c_current = assemble(dot(f, self.u)*dx)
            if MPI.rank(MPI.comm_world) == 0:
                print("Current compliance: ", c_current)
                #print("Current Compliance 2: ", np.sum(project(self.tmpvec ** p * psi(self.u), X).vector()[:])*0.0004)

            return [self.C - c_current]

        def jacobian(self, m):
            J_comp = assemble(dot(f, u)*dx)
            m_comp = Control(x)
            dJ_comp = compute_gradient(J_comp, m_comp)
            print("Computed Derivative: ", dJ_comp.vector()[:])
            return [-dJ_comp.vector()]

        def output_workspace(self):
            return [0.0]

        def length(self):
            """Return the number of components in the constraint vector (here, one)."""
            return 1  

    problem = MinimizationProblem(Jhat, bounds=(lb, ub), constraints = [StressConstraint(S_max), ComplianceConstraint(C_max), ExtensionConstraint()])
    parameters = {"acceptable_tol": 1.0e-3, "maximum_iterations": 1000}

    solver = IPOPTSolver(problem, parameters=parameters)
    rho_opt = solver.solve()

    File("output2/final_solution.pvd") << rho_opt
    xdmf_filename = XDMFFile(MPI.comm_world, "output2/final_solution.xdmf")
    xdmf_filename.write(rho_opt)