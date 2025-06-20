/**
 * @name Path traversal vulnerability in FastAPI file operations
 * @description Detects potential path traversal vulnerabilities in FastAPI file handling
 * @kind path-problem
 * @problem.severity error
 * @security-severity 8.5
 * @precision high
 * @id py/fastapi-path-traversal
 * @tags security
 *       path-traversal
 *       fastapi
 *       external/cwe/cwe-022
 */

import python
import semmle.python.dataflow.new.DataFlow
import semmle.python.dataflow.new.TaintTracking
import semmle.python.ApiGraphs
import semmle.python.dataflow.new.RemoteFlowSources

/**
 * A taint-tracking configuration for path traversal vulnerabilities
 */
class FastAPIPathTraversalConfig extends TaintTracking::Configuration {
  FastAPIPathTraversalConfig() { this = "FastAPIPathTraversalConfig" }

  override predicate isSource(DataFlow::Node source) {
    // User-controlled file paths from FastAPI
    source instanceof FastAPIFilePathSource
  }

  override predicate isSink(DataFlow::Node sink) {
    // File system operations
    exists(DataFlow::Node call |
      (
        // Built-in file operations
        call.asExpr() instanceof FileOpen or
        // os.path operations
        call = API::moduleImport("os.path").getMember(["join", "abspath", "realpath", "normpath"]).getACall() or
        // Path operations
        call = API::moduleImport("pathlib").getMember("Path").getACall() or
        // shutil operations
        call = API::moduleImport("shutil").getMember(["copy", "copy2", "copyfile", "move"]).getACall() or
        // os operations
        call = API::moduleImport("os").getMember(["remove", "unlink", "rmdir", "mkdir", "makedirs", "rename"]).getACall()
      ) and
      sink = call.getArg(0)
    )
    or
    // FastAPI FileResponse
    exists(DataFlow::Node response |
      response = API::moduleImport("fastapi.responses").getMember("FileResponse").getACall() and
      sink = response.getArg(0)
    )
  }

  override predicate isSanitizer(DataFlow::Node node) {
    // Path validation/sanitization
    exists(DataFlow::Node call |
      (
        // Safe path joining with validation
        call = API::moduleImport("os.path").getMember(["basename", "normpath", "realpath"]).getACall() or
        // Path validation methods
        call.asExpr().(Call).getFunc().(Attribute).getName() = ["is_safe_path", "validate_path", "sanitize_path"]
      ) and
      node = call
    )
    or
    // Checks for path traversal patterns
    exists(DataFlow::Node check |
      check.asExpr() instanceof Compare and
      check.asExpr().(Compare).getOp(0) instanceof In and
      check.asExpr().(Compare).getComparator(0).(Str).getText().matches(["%..%", "%/%", "%\\%"]) and
      node = check
    )
  }
}

/**
 * Sources of file paths in FastAPI applications
 */
class FastAPIFilePathSource extends RemoteFlowSource {
  FastAPIFilePathSource() {
    // Path parameters containing file paths
    exists(DataFlow::Node param |
      param = API::moduleImport("fastapi").getMember("Path").getACall() and
      param.asExpr().(Call).getArgByName("description").getAConstantValue().getString().toLowerCase().matches(["%file%", "%path%", "%name%"]) and
      this = param
    )
    or
    // Query parameters for file paths
    exists(DataFlow::Node param |
      param = API::moduleImport("fastapi").getMember("Query").getACall() and
      param.asExpr().(Call).getArgByName("description").getAConstantValue().getString().toLowerCase().matches(["%file%", "%path%", "%name%"]) and
      this = param
    )
    or
    // File upload filenames
    exists(DataFlow::Node upload |
      upload = API::moduleImport("fastapi").getMember("UploadFile").getReturn() and
      this = upload.getMember("filename")
    )
    or
    // Form data containing file paths
    exists(DataFlow::Node form |
      form = API::moduleImport("fastapi").getMember("Form").getACall() and
      this = form
    )
  }

  override string getSourceType() { 
    result = "FastAPI user-controlled file path" 
  }
}

/**
 * Identifies file open operations
 */
class FileOpen extends Call {
  FileOpen() {
    this.getFunc().(Name).getId() = "open" or
    this.getFunc().(Attribute).getName() = "open"
  }
}

from FastAPIPathTraversalConfig config, DataFlow::PathNode source, DataFlow::PathNode sink
where config.hasFlowPath(source, sink)
select sink.getNode(), source, sink,
  "This file operation may be vulnerable to path traversal from $@.",
  source.getNode(), "user-controlled input"