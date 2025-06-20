/**
 * @name SQL injection vulnerability in FastAPI
 * @description Detects potential SQL injection vulnerabilities in FastAPI applications
 * @kind path-problem
 * @problem.severity error
 * @security-severity 9.0
 * @precision high
 * @id py/fastapi-sql-injection
 * @tags security
 *       sql-injection
 *       fastapi
 *       external/cwe/cwe-089
 */

import python
import semmle.python.dataflow.new.DataFlow
import semmle.python.dataflow.new.TaintTracking
import semmle.python.ApiGraphs
import semmle.python.dataflow.new.RemoteFlowSources

/**
 * A taint-tracking configuration for SQL injection vulnerabilities in FastAPI
 */
class FastAPISqlInjectionConfig extends TaintTracking::Configuration {
  FastAPISqlInjectionConfig() { this = "FastAPISqlInjectionConfig" }

  override predicate isSource(DataFlow::Node source) {
    // FastAPI request parameters
    exists(DataFlow::Node param |
      param = any(FastAPIRequestParameter p).getAUse() and
      source = param
    )
    or
    // Path parameters
    source instanceof PathParameter
    or
    // Query parameters
    source instanceof QueryParameter
    or
    // Request body data
    source instanceof RequestBodyData
  }

  override predicate isSink(DataFlow::Node sink) {
    // SQL query execution methods
    exists(DataFlow::Node query |
      (
        // SQLAlchemy raw queries
        query = API::moduleImport("sqlalchemy").getMember("text").getACall() or
        query = API::moduleImport("sqlalchemy.orm").getMember("Session").getReturn().getMember("execute").getACall() or
        // Direct database cursor execution
        query.asExpr().(Call).getFunc().(Attribute).getName() = ["execute", "executemany", "executescript"] and
        query.asExpr().(Call).getFunc().(Attribute).getObject().getType().getName().matches(["%cursor%", "%connection%"])
      ) and
      sink = query.getArg(0)
    )
  }

  override predicate isSanitizer(DataFlow::Node node) {
    // Parameterized queries are safe
    exists(DataFlow::Node call |
      call = API::moduleImport("sqlalchemy").getMember("text").getACall() and
      call.asExpr().(Call).getArgByName("bindparams") != none() and
      node = call
    )
    or
    // ORM query builders are generally safe
    node.asExpr().getType().getName().matches(["%Query%", "%Select%", "%Insert%", "%Update%", "%Delete%"])
  }
}

/**
 * FastAPI request parameters
 */
class FastAPIRequestParameter extends DataFlow::Node {
  FastAPIRequestParameter() {
    // Path parameters
    exists(string paramType |
      paramType = ["Path", "Query", "Header", "Cookie", "Form", "File", "Body"] and
      this = API::moduleImport("fastapi").getMember(paramType).getACall()
    )
  }
}

/**
 * Path parameters in FastAPI
 */
class PathParameter extends RemoteFlowSource {
  PathParameter() {
    this = API::moduleImport("fastapi").getMember("Path").getACall()
  }

  override string getSourceType() { result = "FastAPI path parameter" }
}

/**
 * Query parameters in FastAPI
 */
class QueryParameter extends RemoteFlowSource {
  QueryParameter() {
    this = API::moduleImport("fastapi").getMember("Query").getACall()
  }

  override string getSourceType() { result = "FastAPI query parameter" }
}

/**
 * Request body data in FastAPI
 */
class RequestBodyData extends RemoteFlowSource {
  RequestBodyData() {
    this = API::moduleImport("fastapi").getMember("Body").getACall()
    or
    // Pydantic model instances used as request bodies
    exists(DataFlow::Node model |
      model.getType().getName().matches("%BaseModel%") and
      this = model
    )
  }

  override string getSourceType() { result = "FastAPI request body" }
}

from FastAPISqlInjectionConfig config, DataFlow::PathNode source, DataFlow::PathNode sink
where config.hasFlowPath(source, sink)
select sink.getNode(), source, sink,
  "This SQL query may be vulnerable to injection from $@.",
  source.getNode(), "user input"