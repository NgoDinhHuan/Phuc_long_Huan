import onnx_graphsurgeon as gs
import onnx
graph1 = gs.import_onnx(onnx.load("par_2609.onnx"))
tensors = graph1.tensors()
tensors["input"].shape[0] = gs.Tensor.DYNAMIC
onnx.save(gs.export_onnx(graph1.cleanup().toposort()), "par_2609_dynamic.onnx")