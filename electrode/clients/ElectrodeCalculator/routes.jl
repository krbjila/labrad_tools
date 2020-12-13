using Genie.Router
using CalculatorController
import Genie.Renderer.Json: json
using Genie.Requests

route("/") do
  serve_static_file("welcome.html")
end

route("/params", method = POST) do
  message = jsonpayload()
  V = [message[k] for k in CalculatorController.KEY_ORDER]
  CalculatorController.params_json(V) |> json
end

route("/opt", method = POST) do
  message = jsonpayload()
  p = [message[k] for k in CalculatorController.PARAM_ORDER]
  CalculatorController.opt_json(p) |> json
end