module CalculatorController
  using JSON
  using TypedPolynomials
  using StaticArrays
  using LinearAlgebra
  using Optim
  using ReverseDiff
  using DiffResults
  using BenchmarkTools

  if !(@isdefined coeffs)
      # Configuration constants
      const PATH = "../lib/efield/comsol/data/fit_coeffs.json"
      const KEY_ORDER = ["LP", "UP", "LW", "LE", "UE", "UW"]
      const PARAM_ORDER = ["bias", "dipole", "angle", "dEdx", "dEdy", "nux", "nuy"]

      # Optimization constants
      const weights = SA_F64[1, 0, 1, 1, 1, 0, 0]

      # Physical constants
      const amu = 1.66054e-27 # kg
      const DVcmToJ = 3.33564e-28 # J

      # Physical parameters for KRb
      const D_POLY_FIT = SA_F64[0, 0.0561, -0.00337, 1.03812e-4, -1.42283e-6, 5.34778e-9]
      const m = 127*amu

      # Polynomial orders
      const xorder = 7
      const yorder = 7

      # Location to evaluate polynomials
      const xval = 0.0
      const yval = 0.0

      # Load JSON with polynomial coefficients
      const coeffs = JSON.parsefile(PATH)

      # Construct potential as polynomial
      @polyvar x y
      const monomials = [10^(i + j) * x^i * y^j for i in 0:xorder for j in 0:yorder]
      const Vpoly = [dot(convert(Vector{Float64}, coeffs[k]), monomials) for k in KEY_ORDER]

      # Compute polynomials corresponding to electric field and its derivatives
      const Epoly = SMatrix{6,2}([differentiate(-v, var) for v in Vpoly, var in [x, y]])
      const dEdxpoly = SMatrix{6,2}([differentiate.(e, x) for e in Epoly])
      const dEdypoly = SMatrix{6,2}([differentiate.(e, y) for e in Epoly])
      const d2Edx2poly = SMatrix{6,2}([differentiate.(de, x) for de in dEdxpoly])
      const d2Edy2poly = SMatrix{6,2}([differentiate.(de, y) for de in dEdypoly])

      # Evaluate polynomials corresponding to electric field and its derivatives
      const ExV = subs.(Epoly, (x, y) => (xval, yval))
      const dEdxV = subs.(dEdxpoly, (x, y) => (xval, yval))
      const dEdyV = subs.(dEdypoly, (x, y) => (xval, yval))
      const d2Edx2V = subs.(d2Edx2poly, (x, y) => (xval, yval))
      const d2Edy2V = subs.(d2Edy2poly, (x, y) => (xval, yval))

      # Construct dipole moment and its derivatives as polynomials
      @polyvar E
      const Dpoly = dot(D_POLY_FIT, [(E/1000)^i for i in 0:length(D_POLY_FIT)-1])
      const dDdEpoly = differentiate(Dpoly, E)
      const d2DdE2poly = differentiate(dDdEpoly, E)
  end

  # Compute the parameters of the field given electrode potentials
  function get_params(V)
      # Evaluate the electric field and its derivatives given electrode potentials
      Ev = sum(ExV .* V, dims=1)
      dEdxv = sum(dEdxV .* V, dims=1)
      dEdyv = sum(dEdyV .* V, dims=1)
      d2Edx2v = sum(d2Edx2V .* V, dims=1)
      d2Edy2v = sum(d2Edy2V .* V, dims=1)

      # Compute the electric field magnitude, direction and gradient
      bias = norm(Ev)
      angle = atan(Ev[1], Ev[2]) * 180/π
      dEdx = dot(Ev, dEdxv)/bias
      dEdy = dot(Ev, dEdyv)/bias

      # Evaluate the dipole moment at the bias field and its derivatives
      dipole = subs(Dpoly, E => bias)
      dDdEv = subs(dDdEpoly, E => bias)
      d2DdE2v = subs(d2DdE2poly, E => bias)

      # Compute the trap frequency
      kx = (dipole/bias + dDdEv) * dot(Ev, d2Edx2v) + dEdx^2 * (2 * dDdEv + bias * d2DdE2v)
      ky = (dipole/bias + dDdEv) * dot(Ev, d2Edy2v) + dEdy^2 * (2 * dDdEv + bias * d2DdE2v)
      # TODO: Correct these formulae after testing program
      νx = sqrt(abs(100*DVcmToJ*kx) / (2 * π * m))
      νy = sqrt(abs(100*DVcmToJ*ky) / (2 * π * m))

      out = SVector(bias, dipole, angle, dEdx, dEdy, νx, νy)

      return out
  end

  # Compute the least squares error
  function err(p, V)
      return dot(weights, (get_params(V) .- p).^2)
  end

  # Optimize electrode potentials for parameters p
  function opt(p; V0=Nothing)
      if V0 == Nothing
          V0 = randn(6)
      end
      f(V) = err(p, V)
      tape = ReverseDiff.GradientTape(f, V0)
      compiled_tape = ReverseDiff.compile(tape)
      result = DiffResults.GradientResult(V0)
      function fg!(F, G, V)
          ReverseDiff.gradient!(result, compiled_tape, V)
          G .= DiffResults.gradient(result)
          return DiffResults.value(result)
      end
      opts = Optim.Options(x_tol=1E-8, f_tol=1E-8, g_tol=1E-8)
      optimize(Optim.only_fg!(fg!), V0, BFGS(), opts)
  end

  function opt_json(p; V0=Nothing)
    min = opt(p; V0=V0).minimizer
    p = get_params(min)
    Vdict = Dict(k => min[i] for (i, k) in enumerate(KEY_ORDER))
    pdict = Dict(k => p[i] for (i, k) in enumerate(PARAM_ORDER))
    return json(merge(Vdict, pdict))
  end

  function params_json(V)
    p = get_params(V)
    return json(Dict(k => p[i] for (i, k) in enumerate(PARAM_ORDER)))
  end

  # Benchmark the optimization
  # goal = [12446.91, 0, 45, 250, 63.83, 0, 0]
  # println("\nBenchmark:")
  # @benchmark opt(x) setup=(x = randn(length(goal)))
end