module ElectrodeCalculator

using Logging, LoggingExtras

function main()
  Base.eval(Main, :(const UserApp = ElectrodeCalculator))

  include(joinpath("..", "genie.jl"))

  Base.eval(Main, :(const Genie = ElectrodeCalculator.Genie))
  Base.eval(Main, :(using Genie))
end; main()

end
