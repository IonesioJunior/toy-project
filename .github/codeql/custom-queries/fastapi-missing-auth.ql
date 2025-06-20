/**
 * @name Missing authentication on FastAPI endpoint
 * @description Detects FastAPI route handlers that may be missing authentication dependencies
 * @kind problem
 * @problem.severity error
 * @security-severity 8.0
 * @precision medium
 * @id py/fastapi-missing-auth
 * @tags security
 *       authentication
 *       fastapi
 */

import python
import semmle.python.dataflow.new.DataFlow
import semmle.python.ApiGraphs

/**
 * Identifies FastAPI route decorators
 */
class FastAPIRouteDecorator extends DataFlow::Node {
  FastAPIRouteDecorator() {
    exists(string method |
      method = ["get", "post", "put", "delete", "patch", "options", "head"] and
      this = API::moduleImport("fastapi").getMember("APIRouter").getReturn().getMember(method).getACall()
    )
    or
    exists(string method |
      method = ["get", "post", "put", "delete", "patch", "options", "head"] and
      this = API::moduleImport("fastapi").getMember("FastAPI").getReturn().getMember(method).getACall()
    )
  }
}

/**
 * Identifies authentication dependencies in FastAPI
 */
class AuthenticationDependency extends DataFlow::Node {
  AuthenticationDependency() {
    // Direct authentication dependencies
    exists(DataFlow::Node depends |
      depends = API::moduleImport("fastapi").getMember("Depends").getACall() and
      this = depends.getArg(0) and
      (
        // Common auth patterns
        this.asExpr().(Name).getId().matches(["%auth%", "%security%", "%token%", "%jwt%", "%oauth%"])
        or
        // FastAPI security utilities
        exists(string authClass |
          authClass = ["HTTPBearer", "HTTPBasic", "OAuth2PasswordBearer", 
                       "APIKeyHeader", "APIKeyQuery", "APIKeyCookie"] and
          this = API::moduleImport("fastapi.security").getMember(authClass).getReturn()
        )
      )
    )
  }
}

/**
 * Checks if a function has authentication in its parameters
 */
predicate hasAuthentication(Function func) {
  exists(Parameter param |
    param = func.getAParameter() and
    exists(AuthenticationDependency auth |
      auth.asExpr() = param.getDefault()
    )
  )
}

/**
 * Identifies public endpoints (paths that typically don't require auth)
 */
predicate isPublicEndpoint(string path) {
  path.matches(["/health%", "/docs%", "/openapi%", "/redoc%", "/", "/login%", "/register%", "/public%"])
}

from FastAPIRouteDecorator decorator, Function handler, string path
where
  // Get the handler function
  handler = decorator.asExpr().(Call).getASuccessor().(Call).getArg(0).getALocalSource().asExpr() and
  // Get the path from the decorator
  path = decorator.asExpr().(Call).getArg(0).getAConstantValue().getString() and
  // Check if it's not a public endpoint
  not isPublicEndpoint(path) and
  // Check if the handler doesn't have authentication
  not hasAuthentication(handler)
select handler, "This FastAPI endpoint at '" + path + "' appears to be missing authentication. Consider adding a security dependency."