using Genie.Router
using CalculatorController
import Genie.Renderer.Json: json
using Genie.Requests

route("/") do
  serve_static_file("welcome.html")
end

route("/params", method = POST) do
  messages = jsonpayload()
  out = Dict()
  for mk in keys(messages)
    message = messages[mk]
    out[mk] = [CalculatorController.params_json([point[k] for k in CalculatorController.KEY_ORDER]) for point in message]
  end
  return out |> json
end

route("/opt", method = POST) do
  messages = jsonpayload()
  out = Dict()
  for mk in keys(messages)
    message = messages[mk]
    last_result = nothing
    last_weight = nothing
    out[mk] = []
    for point in message
      p = [point[k] for k in CalculatorController.PARAM_ORDER]
      if CalculatorController.KEY_ORDER[1] in keys(point)
        V0 = [convert(Float64, point[v]) for v in CalculatorController.KEY_ORDER]
      elseif last_result !== nothing
        V0 = last_result
      else
        V0 = nothing
      end
      if "weights" in keys(point)
        w = [convert(Float64, point["weights"][k]) for k in CalculatorController.PARAM_ORDER]
      elseif last_weight !== nothing
        w = last_weight
      else
        w = CalculatorController.weights
      end
      result = CalculatorController.opt_json(p; V0=V0, w=w)
      last_result = [convert(Float64, result[v]) for v in CalculatorController.KEY_ORDER]
      last_weight = w
      append!(out[mk], result)
    end
  end
  return out |> json
end