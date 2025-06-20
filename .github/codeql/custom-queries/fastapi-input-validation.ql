/**
 * @name Insufficient input validation in FastAPI
 * @description Detects FastAPI endpoints that may have insufficient input validation
 * @kind problem
 * @problem.severity warning
 * @security-severity 6.5
 * @precision medium
 * @id py/fastapi-input-validation
 * @tags security
 *       input-validation
 *       fastapi
 *       external/cwe/cwe-020
 */

import python
import semmle.python.dataflow.new.DataFlow
import semmle.python.ApiGraphs

/**
 * FastAPI endpoint handlers
 */
class FastAPIEndpoint extends Function {
  FastAPIEndpoint() {
    exists(Call decorator |
      decorator = this.getADecorator() and
      decorator.getFunc().(Attribute).getName() in 
        ["get", "post", "put", "delete", "patch", "options", "head"]
    )
  }
}

/**
 * Parameters that accept raw strings without validation
 */
class UnvalidatedStringParameter extends Parameter {
  UnvalidatedStringParameter() {
    exists(FastAPIEndpoint endpoint |
      this = endpoint.getAParameter() and
      // Has string type annotation
      (
        this.getAnnotation().(Name).getId() = "str" or
        this.getAnnotation().(Attribute).getName() = "str"
      ) and
      // No FastAPI validation
      not exists(Call validation |
        validation = this.getDefault() and
        validation.getFunc().(Name).getId() in ["Query", "Path", "Body", "Form", "Header", "Cookie"]
      ) and
      // Not a dependency injection
      not exists(Call depends |
        depends = this.getDefault() and
        depends.getFunc().(Name).getId() = "Depends"
      )
    )
  }
}

/**
 * Query/Path parameters without constraints
 */
class UnconstrainedParameter extends DataFlow::Node {
  string paramType;
  string paramName;
  
  UnconstrainedParameter() {
    exists(Call param, string pType |
      pType in ["Query", "Path", "Header", "Cookie", "Form"] and
      param = API::moduleImport("fastapi").getMember(pType).getACall().asExpr() and
      paramType = pType and
      this.asExpr() = param and
      // Get parameter name from the function parameter
      exists(Parameter funcParam |
        funcParam.getDefault() = param and
        paramName = funcParam.getName()
      ) and
      // No validation constraints
      not exists(string constraint |
        constraint in ["min_length", "max_length", "regex", "gt", "ge", "lt", "le", 
                      "multiple_of", "min_items", "max_items"] and
        param.getArgByName(constraint) != none()
      )
    )
  }
  
  string getParameterType() { result = paramType }
  string getParameterName() { result = paramName }
}

/**
 * Pydantic models without field validation
 */
class UnvalidatedPydanticField extends Assign {
  string fieldName;
  Class modelClass;
  
  UnvalidatedPydanticField() {
    exists(Class cls |
      cls.getABase().getName() = "BaseModel" and
      this.getScope() = cls and
      modelClass = cls and
      fieldName = this.getTarget(0).(Name).getId() and
      // String or list fields without validation
      (
        this.getValue().(Name).getId() in ["str", "list", "dict"] or
        exists(Subscript sub |
          sub = this.getValue() and
          sub.getObject().(Name).getId() in ["List", "Dict", "Set"]
        )
      ) and
      // No Field() with validators
      not exists(Call field |
        field = this.getValue() and
        field.getFunc().(Name).getId() = "Field" and
        exists(string validator |
          validator in ["min_length", "max_length", "regex", "min_items", "max_items"] and
          field.getArgByName(validator) != none()
        )
      )
    )
  }
  
  string getFieldName() { result = fieldName }
  Class getModelClass() { result = modelClass }
}

/**
 * Direct use of request data without validation
 */
class UnvalidatedRequestData extends DataFlow::Node {
  UnvalidatedRequestData() {
    exists(Attribute attr |
      attr.getObject().(Name).getId() = "request" and
      attr.getName() in ["query_params", "path_params", "headers", "cookies"] and
      this.asExpr() = attr
    )
  }
}

// Find input validation issues
from AstNode node, string message
where
  // Case 1: String parameters without validation
  exists(UnvalidatedStringParameter param |
    node = param and
    message = "Parameter '" + param.getName() + "' accepts raw string input without FastAPI validation. " +
              "Consider using Query(), Path(), or Body() with validation constraints."
  )
  or
  // Case 2: FastAPI parameters without constraints
  exists(UnconstrainedParameter param |
    node = param.asExpr() and
    message = param.getParameterType() + " parameter '" + param.getParameterName() + 
              "' lacks validation constraints. Consider adding min_length, max_length, or regex validation."
  )
  or
  // Case 3: Pydantic fields without validation
  exists(UnvalidatedPydanticField field |
    node = field and
    message = "Pydantic model field '" + field.getFieldName() + "' in " + field.getModelClass().getName() +
              " lacks validation. Consider using Field() with validators."
  )
  or
  // Case 4: Direct request data access
  exists(UnvalidatedRequestData data |
    node = data.asExpr() and
    message = "Direct access to request data without validation. " +
              "Consider using FastAPI's parameter validation instead."
  )
select node, message