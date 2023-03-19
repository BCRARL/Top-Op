import numpy as np
import math
from fenics import *
from dolfin import *
import ufl as ufl
from ufl import nabla_div
from fenics_adjoint import *
from pyadjoint import ipopt


def massopt3Dsolver(solution2d):
    L = 2.0                                         # Length
    W = 1.0                                         # Width
    D = 0.5                                         # Depth
    p = Constant(5.0)                               # Penalization Factor for SIMP
    p_norm = Constant(8.0)                          # P-Normalization Term
    q = Constant(0.5)                               # Relaxation Factor for Stress
    eps = Constant(1.0e-3)                          # Epsilon value for SIMP to remove singularities
    nu = Constant(0.3)                              # Poisson's Ratio
    Y = Constant(2.0e+11)                           # Young Modulus
    nelx = 100                                      # Number of elements in x-direction
    nely = 50                                       # Number of elements in y-direction
    nelz = 5                                        # Number of elements in z-direction
    C_max = Constant(2.0e-3)                        # Max Compliance
    S_max = Constant(3.0e+7)                        # Max Stress
    r = Constant(0.025)                             # Length Parameter for Helmholtz Filter
    b_rad = Constant(0.025)                         # Radius for boundary around circles
    radii = np.array([0.20, 0.15, 0.15])            # Radii for circles
    circle_coords = np.array([[0.67, 1.0, 1.4], [0.75, 0.25, 0.60]])
    loads = np.array([[15000.0, 0.0, -15000.0], [5000.0, -10000.0, 5000.0]])



    mesh = BoxMesh(Point(0.0, 0.0, 0.0), Point(L, W, D), nelx, nely, nelz)

    # Create Subdomains for Circular Voids / Cylinders and their Borders
    circle_1 = CompiledSubDomain('(x[0]-x_)*(x[0]-x_) + (x[1]-y_)*(x[1]-y_) <= r*r + tol', x_=circle_coords[0][0], y_=circle_coords[1][0], r=radii[0], tol=DOLFIN_EPS)
    circle_2 = CompiledSubDomain('(x[0]-x_)*(x[0]-x_) + (x[1]-y_)*(x[1]-y_) <= r*r + tol', x_=circle_coords[0][1], y_=circle_coords[1][1], r=radii[1], tol=DOLFIN_EPS)
    circle_3 = CompiledSubDomain('(x[0]-x_)*(x[0]-x_) + (x[1]-y_)*(x[1]-y_) <= r*r + tol', x_=circle_coords[0][2], y_=circle_coords[1][2], r=radii[2], tol=DOLFIN_EPS)

    boundary_1 = CompiledSubDomain('(x[0]-x_)*(x[0]-x_) + (x[1]-y_)*(x[1]-y_) <= pow(r+b_rad, 2) + tol', x_=circle_coords[0][0], y_=circle_coords[1][0], r=radii[0], b_rad = b_rad, tol=DOLFIN_EPS)
    boundary_2 = CompiledSubDomain('(x[0]-x_)*(x[0]-x_) + (x[1]-y_)*(x[1]-y_) <= pow(r+b_rad, 2) + tol', x_=circle_coords[0][1], y_=circle_coords[1][1], r=radii[1], b_rad = b_rad, tol=DOLFIN_EPS)
    boundary_3 = CompiledSubDomain('(x[0]-x_)*(x[0]-x_) + (x[1]-y_)*(x[1]-y_) <= pow(r+b_rad, 2) + tol', x_=circle_coords[0][2], y_=circle_coords[1][2], r=radii[2], b_rad = b_rad, tol=DOLFIN_EPS)

    # Initialize mesh function for interior domains
    domains = MeshFunction("size_t", mesh, mesh.topology().dim())
    domains.set_all(0)
    boundary_1.mark(domains, 4)
    boundary_2.mark(domains, 4)
    boundary_3.mark(domains, 4)
    circle_1.mark(domains, 1)
    circle_2.mark(domains, 2)
    circle_3.mark(domains, 3)
    
    # Define new measures associated with the interior domains
    dx = Measure('dx', domain = mesh, subdomain_data = domains)

    # Define Function Spaces
    U = VectorFunctionSpace(mesh, "Lagrange", 1) # Displacement Function Space
    X = FunctionSpace(mesh, "Lagrange", 1)       # Density Function Space

    # Creating Function for Youngs Modulus across Mesh
    Q = FunctionSpace(mesh, "DG", 0)
    E = Function(Q)
    e_ = Q.tabulate_dof_coordinates()

    for i in range(e_.shape[0]):
        if domains.array()[i] == 1 or domains.array()[i] == 2 or domains.array()[i] == 3:
            E.vector().vec().setValueLocal(i, Constant(1.0e+22))
        else:
            E.vector().vec().setValueLocal(i, Y)

    lmbda = (E*nu) / ((1.0 + nu)*(1.0 - (2.0*nu)))  # Lame's first parameter
    G = E / (2.0*(1.0 + nu))                        # Lame's second parameter / Shear Modulus

    # Build Rotation Matrix
    R = np.zeros((2,2))
    R[0][0] = 0.0
    R[0][1] = -1.0
    R[1][0] = 1.0
    R[1][1] = 0.0

    # Function to generate rotated loads to account for torque
    def generate_loads(rho):
        F_new = np.zeros(loads.shape)
        x_c = np.zeros(loads.shape)
        (x_,y_,z_) = SpatialCoordinate(mesh)

        # Calculate center of mass 
        cm_x = assemble(rho*x_*dx)/assemble(rho*dx)
        cm_y = assemble(rho*y_*dx)/assemble(rho*dx)

        # Set load points w.r.t. center of mass
        for i in range(len(circle_coords[0])):
            x_c[0][i] = circle_coords[0][i] - cm_x
            x_c[1][i] = circle_coords[1][i] - cm_y

        # Removal of rotational component of loads
        denom = np.trace(x_c.T.dot(loads)) 
        if np.abs(denom) >= DOLFIN_EPS:
            theta = math.atan2(np.trace((x_c.T.dot(R)).dot(loads)), np.trace(x_c.T.dot(loads)))
            F_rot = R.dot(loads) * math.sin(theta)
            F_new = loads * math.cos(theta) + F_rot
        else:
            F_new = -R.dot(loads)

        # Creating Function for Load Vectors across Mesh
        F = VectorFunctionSpace(mesh, "DG", 0)
        f = Function(F)
        f_ = F.tabulate_dof_coordinates().reshape(e_.shape[0], mesh.topology().dim(), mesh.topology().dim())

        # Generate Load Function over mesh
        ds_ = np.array([assemble(rho*dx(i)) for i in range(1,4)])
        for i in range(f_.shape[0]):
            j = domains.array()[i]
            if j in [1,2,3]:
                k=int(j-1)
                f.vector().vec().setValueLocal(2*i, F_new[0][k] / ds_[k])
                f.vector().vec().setValueLocal(2*i+1, F_new[1][k] / ds_[k])
                f.vector().vec().setValueLocal(2*i+2, 0.0)
            else:
                f.vector().vec().setValueLocal(2*i, 0.0)
                f.vector().vec().setValueLocal(2*i+1, 0.0)
                f.vector().vec().setValueLocal(2*i+2, 0.0)
        
        return f

    # SIMP Function for Intermediate Density Penalization
    def simp(x):
        return eps + (1 - eps) * x**p

    # Calculate Strain from Displacements u
    def strain(u):
        return 0.5*(nabla_grad(u) + nabla_grad(u).T)

    # Calculate Cauchy Stress Matrix from Displacements u
    def sigma(u):
        return lmbda*nabla_div(u)*Identity(mesh.topology().dim()) + 2*G*strain(u)

    # Calculate Von Mises Stress from Displacements u
    def von_mises(u):
        VDG = FunctionSpace(mesh, "DG", 0)
        s = sigma(u) - (1./3)*tr(sigma(u))*Identity(mesh.topology().dim()) # Deviatoric Stress
        von_Mises = sqrt(3./2*inner(s, s))
        u, v = TrialFunction(VDG), TestFunction(VDG)
        a = inner(u, v)*dx
        L = inner(von_Mises, v)*dx(0) + inner(von_Mises, v)*dx(4)
        A, b = assemble_system(a, L)
        stress = Function(VDG)
        solve(A, stress.vector(), b, 'mumps')                                                              
        return stress

    # RELU^2 Function for Global Stress Constraint Computation
    def relu(x):                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
        return (x * (ufl.sign(x) + 1) * 0.5) ** 2

    # Helmholtz Filter for Design Variables. Helps remove checkerboarding and introduces mesh independency.
    # Taken from work done by de Souza et al. (2020)
    def helmholtz_filter(rho_n):
        V = rho_n.function_space()

        rho = TrialFunction(V)
        w = TestFunction(V)

        a = (r**2)*inner(grad(rho), grad(w))*dx(0) + (r**2)*inner(grad(rho), grad(w))*dx(4) + rho*w*dx
        L = rho_n*w*dx

        A, b = assemble_system(a, L)
        rho = Function(V)
        solve(A, rho.vector(), b, 'mumps')

        return rho

    # Forward problem solution. Solves for displacement u given density x.
    def forward(x):
        rho = helmholtz_filter(x)
        u = TrialFunction(U)  # Trial Function
        v = TestFunction(U)   # Test Function
        f = generate_loads(rho)
        a = simp(rho)*inner(sigma(u), strain(v))*dx
        L = dot(f, v)*dx
        A, b = assemble_system(a, L)
        u = Function(U)
        solve(A, u.vector(), b, 'mumps')
        return (f, u)

    # MAIN
    def main():
        x = interpolate(Constant(0.99), X)
        (f, u) = forward(x)
        vm = von_mises(u) 
        S_min = vm.vector()[:].max()
        C_min = assemble(dot(f,u)*dx)
        #C_max = C_min * 5
        #S_max = S_min * 300
        x = interpolate(solution2d, X)

        #iteration_count = 0
        (f, u) = forward(x)                 # Forward problem
        vm = von_mises(u)                   # Calculate Von Mises Stress for outer subdomain

        solution_list = []
        derivative_list = []
        def derivative_cb(j, dj, m):
            solution_list.append(m.vector()[:])
            derivative_list.append(dj.vector()[:])
            
        # Objective Functional to be Minimized
        J = assemble(x*dx(0))
        m = Control(x)  # Control
        Jhat = ReducedFunctional(J, m, derivative_cb_post = derivative_cb) # Reduced Functional

        lb = 0.0  # Inferior
        ub = 1.0  # Superior

        # Class for Enforcing Compliance Constraint
        class ComplianceConstraint(InequalityConstraint):
            def __init__(self, C):
                self.C  = float(C)

            def function(self, m):
                c_current = assemble(dot(Control(f).tape_value(), Control(u).tape_value())*dx) # Uses the value of u stored in the dolfin adjoint tape
                if MPI.rank(MPI.comm_world) == 0:
                    print("Current compliance: ", c_current)
                
                return [self.C - c_current]

            def jacobian(self, m):
                J_comp = assemble(dot(f, u)*dx)
                m_comp = Control(x)
                dJ_comp = compute_gradient(J_comp, m_comp) # compute_gradient() uses the current value of u stored in the dolfin adjoint tape
                if MPI.rank(MPI.comm_world) == 0:
                    print("Computed Derivative: ", -(dJ_comp.vector()[:]))

                return [-dJ_comp.vector()]

            def output_workspace(self):
                return [0.0]

            def length(self):
                """Return the number of components in the constraint vector (here, one)."""
                return 1
        
        # Class for Enforcing Stress Constraint
        class StressConstraint(InequalityConstraint):
            def __init__(self, S, q):
                self.S  = float(S)
                self.q = float(q)
                self.temp_x = Function(X)

            def function(self, m):
                self.temp_x.vector()[:] = m
                print("Current control vector (density): ", self.temp_x.vector()[:])
                s_current = assemble(relu(Control(vm).tape_value()*(Control(x).tape_value()**self.q)-self.S)*dx)
                if MPI.rank(MPI.comm_world) == 0:
                    print("Current stress: ", s_current)

                return [-s_current]

            def jacobian(self, m):
                self.temp_x.vector()[:] = m
                J_stress = assemble(relu(vm*(x**self.q)-self.S)*dx)
                m_stress = Control(x)
                dJ_stress = compute_gradient(J_stress, m_stress)
                
                return [-dJ_stress.vector()]

            def output_workspace(self):
                return [0.0]

            def length(self):
                """Return the number of components in the constraint vector (here, one)."""
                return 1


        problem = MinimizationProblem(Jhat, bounds=(lb, ub), constraints = [ComplianceConstraint(C_max), StressConstraint(S_max, q)])
        parameters = {"acceptable_tol": 1.0e-3, "maximum_iterations": 100}

        solver = IPOPTSolver(problem, parameters=parameters)
        rho_opt = solver.solve()

        


        return rho_opt
    return main()
    
