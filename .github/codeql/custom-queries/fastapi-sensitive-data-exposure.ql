/**
 * @name Sensitive data exposure in FastAPI responses
 * @description Detects potential exposure of sensitive data in FastAPI API responses
 * @kind problem
 * @problem.severity error
 * @security-severity 7.5
 * @precision high
 * @id py/fastapi-sensitive-data-exposure
 * @tags security
 *       sensitive-data
 *       fastapi
 *       external/cwe/cwe-200
 */

import python
import semmle.python.dataflow.new.DataFlow
import semmle.python.ApiGraphs

/**
 * Identifies sensitive field names that shouldn't be exposed
 */
predicate isSensitiveFieldName(string name) {
  name.toLowerCase().matches([
    "%password%", "%passwd%", "%pwd%", "%secret%", "%token%", 
    "%key%", "%api_key%", "%apikey%", "%auth%", "%credential%",
    "%private%", "%ssn%", "%social_security%", "%credit_card%",
    "%cvv%", "%pin%", "%salt%", "%hash%", "%otp%", "%2fa%",
    "%session%", "%cookie%", "%bearer%", "%refresh_token%"
  ])
}

/**
 * FastAPI response models
 */
class FastAPIResponseModel extends Class {
  FastAPIResponseModel() {
    // Pydantic BaseModel subclasses used in responses
    this.getABase().getName() = "BaseModel" and
    exists(Function endpoint |
      endpoint.getADecorator().(Call).getFunc().(Attribute).getName() in 
        ["get", "post", "put", "delete", "patch"] and
      endpoint.getArgByName("response_model") != none()
    )
  }
}

/**
 * Fields in response models that might expose sensitive data
 */
class SensitiveResponseField extends Assign {
  string fieldName;
  
  SensitiveResponseField() {
    exists(Class cls |
      cls instanceof FastAPIResponseModel and
      this.getScope() = cls and
      fieldName = this.getTarget(0).(Name).getId() and
      isSensitiveFieldName(fieldName)
    )
  }
  
  string getFieldName() { result = fieldName }
}

/**
 * Direct dictionary returns that might contain sensitive data
 */
class SensitiveDictionaryReturn extends Return {
  string sensitiveKey;
  
  SensitiveDictionaryReturn() {
    exists(Dict dict, Str key |
      this.getValue() = dict and
      key = dict.getAKey() and
      sensitiveKey = key.getText() and
      isSensitiveFieldName(sensitiveKey)
    )
  }
  
  string getSensitiveKey() { result = sensitiveKey }
}

/**
 * JSON responses with sensitive data
 */
class SensitiveJSONResponse extends DataFlow::Node {
  string sensitiveField;
  
  SensitiveJSONResponse() {
    exists(DataFlow::Node response, Dict data, Str key |
      response = API::moduleImport("fastapi").getMember("JSONResponse").getACall() and
      data.getAKey() = key and
      sensitiveField = key.getText() and
      isSensitiveFieldName(sensitiveField) and
      this = response
    )
  }
  
  string getSensitiveField() { result = sensitiveField }
}

/**
 * Checks if a field has proper exclusion configuration
 */
predicate hasExclusionConfig(Class cls, string fieldName) {
  exists(Assign config |
    config.getScope() = cls and
    config.getTarget(0).(Name).getId() = fieldName and
    exists(Call field |
      field = config.getValue() and
      field.getFunc().(Name).getId() = "Field" and
      (
        // Check for exclude=True
        field.getArgByName("exclude").getAConstantValue().isTrue() or
        // Check for repr=False (for __repr__ exclusion)
        field.getArgByName("repr").getAConstantValue().isFalse()
      )
    )
  )
}

// Find sensitive data exposures
from AstNode node, string message
where
  // Case 1: Sensitive fields in response models without proper exclusion
  exists(SensitiveResponseField field |
    node = field and
    not hasExclusionConfig(field.getScope(), field.getFieldName()) and
    message = "Response model contains sensitive field '" + field.getFieldName() + 
              "' without proper exclusion. Consider using Field(exclude=True) or removing from response model."
  )
  or
  // Case 2: Direct dictionary returns with sensitive keys
  exists(SensitiveDictionaryReturn ret |
    node = ret and
    message = "Direct return of dictionary containing sensitive key '" + ret.getSensitiveKey() + 
              "'. Consider filtering sensitive data before returning."
  )
  or
  // Case 3: JSONResponse with sensitive data
  exists(SensitiveJSONResponse resp |
    node = resp.asExpr() and
    message = "JSONResponse contains sensitive field '" + resp.getSensitiveField() + 
              "'. Consider removing sensitive data from the response."
  )
select node, message