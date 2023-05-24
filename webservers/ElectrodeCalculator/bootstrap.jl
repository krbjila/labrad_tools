(pwd() != @__DIR__) && cd(@__DIR__) # allow starting app from bin/ dir

using ElectrodeCalculator
const UserApp = ElectrodeCalculator
ElectrodeCalculator.main()
