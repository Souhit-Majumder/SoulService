# SoulService API Contract

## 1. Overview

SoulService connects caterers who have surplus food with recipient institutions that need it. This document defines the conventions and response formats used by the SoulService API.

All API endpoints must follow this contract to ensure consistent communication between the frontend and backend.

## 2. API Conventions

- **API prefix:** `/api/v1`
- **Data exchange format:** XML
- **Character encoding:** UTF-8
- **Content-Type:** `application/xml`
- **Response format:** Every API response must follow the standard XML response envelope defined below.
- **Validation:** Incoming XML must be parsed safely and validated against the appropriate XML Schema Definition (XSD).

## 3. Standard XML Response Envelope

Every API response must use the root element `<response>` and contain the following four elements:

- `<status>`: Indicates whether the operation succeeded or failed. Allowed values are `success` and `error`.
- `<message>`: Provides a human-readable description of the outcome.
- `<data>`: Contains the result of a successful operation. It must be empty when an operation fails.
- `<error>`: Contains structured error information when an operation fails. It must be empty when an operation succeeds.

The order of these elements must remain consistent across responses.

## 4. Successful Responses

Successful responses must set `<status>` to `success`, provide a descriptive `<message>`, include the operation's result inside `<data>`, and leave `<error>` empty.

Example:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<response>
    <status>success</status>
    <message>Food listing retrieved successfully.</message>
    <data>
        <!-- Endpoint-specific data goes here -->
    </data>
    <error/>
</response>
```

The contents of `<data>` will depend on the endpoint. For example, a food-listing endpoint may include the listing identifier, food description, quantity, pickup deadline, and availability status.

## 5. Error Responses

Error responses must set `<status>` to `error`, provide a safe and descriptive `<message>`, leave `<data>` empty, and populate `<error>` with a machine-readable error code and safe details.

Example:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<response>
    <status>error</status>
    <message>Unable to retrieve food listing.</message>
    <data/>
    <error>
        <code>LISTING_NOT_FOUND</code>
        <details>The requested listing does not exist.</details>
    </error>
</response>
```

Error details must never expose stack traces, database queries, internal exceptions, credentials, or other sensitive information.

The API must also return an appropriate HTTP status code alongside the XML response.


## 6. HTTP Status Codes

SoulService must use appropriate HTTP status codes alongside its XML response body.

| HTTP Status | Meaning | Example |
|---|---|---|
| 200 OK | Request completed successfully | Retrieving a food listing |
| 201 Created | A resource was created successfully | Creating a food listing |
| 204 No Content | Successful operation with no response body | Not used with the standard XML envelope |
| 400 Bad Request | Malformed XML or invalid request syntax | XML cannot be parsed |
| 401 Unauthorized | Authentication is missing or invalid | User is not authenticated |
| 403 Forbidden | User lacks permission for the operation | Recipient attempts an administrator action |
| 404 Not Found | Requested resource does not exist | Food listing not found |
| 409 Conflict | Request conflicts with the current resource state | Listing is no longer available |
| 413 Content Too Large | Request body exceeds the allowed size | XML payload exceeds the configured limit |
| 422 Unprocessable Content | XML is well-formed but fails schema or field validation | Required element is missing |
| 500 Internal Server Error | Unexpected server-side failure | Unhandled application error |

Responses that use the standard XML envelope must include a response body, including error responses. Therefore, the API should not use `204 No Content` for those responses.

## 7. Error Codes

Error codes identify specific failure conditions independently of HTTP status codes.

Initial error codes include:

| Error Code | Meaning |
|---|---|
| `MALFORMED_XML` | The request body is not well-formed XML |
| `VALIDATION_ERROR` | The XML does not satisfy the required schema or field rules |
| `UNAUTHORIZED` | Authentication is missing or invalid |
| `FORBIDDEN` | The authenticated user lacks the required permission |
| `LISTING_NOT_FOUND` | The requested food listing does not exist |
| `LISTING_UNAVAILABLE` | The listing cannot be requested or accepted in its current state |
| `REQUEST_NOT_FOUND` | The specified recipient request does not exist |
| `CONFLICT` | The operation conflicts with the current application state |
| `PAYLOAD_TOO_LARGE` | The request body exceeds the configured size limit |
| `INTERNAL_ERROR` | An unexpected server-side error occurred |

The HTTP status code describes the overall outcome of the HTTP request, while the error code identifies the specific application-level failure.

## 8. XML Validation Rules

1. Incoming XML must be parsed using a secure XML parser.
2. XML parsing must reject malformed documents.
3. Incoming XML must be validated against the XSD associated with the endpoint.
4. Required elements, element order, permitted values, and data types must follow the relevant XSD.
5. Application-level business rules must be checked separately from XML schema validation.
6. Request bodies must have a configured size limit.
7. External entity processing and external document retrieval must be disabled to prevent XML External Entity (XXE) attacks.
8. Invalid requests must return an appropriate HTTP status code and a standard XML error response whenever the response body can safely be generated.
9. Internal exceptions and sensitive implementation details must not be exposed to clients.
10. XML responses must use UTF-8 encoding and the appropriate XML content type.


## 9. Create Food Listing

### 9.1 Endpoint

- **Method:** `POST`
- **Path:** `/api/v1/listings`
- **Content-Type:** `application/xml`
- **Accept:** `application/xml`
- **Purpose:** Allows an authenticated caterer to submit a surplus-food listing for recipient institutions.

### 9.2 Request Fields

The request body must contain a `create_listing` root element and conform to `app/xml_api/schemas/listing.xsd`.

| Field | Type | Requirement | Description |
|---|---|---|---|
| `food_name` | String | Required | Name of the surplus food |
| `description` | String | Required | Description of the food |
| `quantity` | Positive integer | Required | Available quantity; must be greater than zero |
| `unit` | String | Required | Measurement unit, e.g. `portions` |
| `prepared_at` | Date-time | Required | Date and time when the food was prepared |
| `pickup_deadline` | Date-time | Required | Latest permitted pickup time |
| `pickup_location` | String | Required | Location where the food can be collected |
| `dietary_infos` | Container | Optional | Contains zero or more `dietary_info` elements |
| `allergens` | Container | Optional | Contains zero or more `allergen` elements |

Dietary information may include values such as `vegetarian` or `vegan`. Allergens may include values such as `peanuts`, `milk`, or `soy`.

Omitting `dietary_infos` or `allergens` means the information was not supplied. An empty container means no entries were supplied. Neither indicates that the food is guaranteed to be free of allergens.

### 9.3 Example Request

```xml
<?xml version="1.0" encoding="UTF-8"?>
<create_listing>
    <food_name>Vegetable Rice</food_name>
    <description>Freshly prepared vegetable rice</description>
    <quantity>15</quantity>
    <unit>portions</unit>
    <prepared_at>2026-10-17T11:30:00</prepared_at>
    <pickup_deadline>2026-10-17T14:00:00</pickup_deadline>
    <pickup_location>Manipal, Karnataka</pickup_location>
    <dietary_infos>
        <dietary_info>vegetarian</dietary_info>
    </dietary_infos>
    <allergens>
        <allergen>peanuts</allergen>
    </allergens>
</create_listing>
```

### 9.4 Validation Rules

1. The request body must contain well-formed XML.
2. The XML must conform to `listing.xsd`.
3. Required text fields must not be empty or consist only of whitespace.
4. `quantity` must be a positive integer.
5. `prepared_at` and `pickup_deadline` must contain valid date-time values.
6. `pickup_deadline` must be later than `prepared_at`.
7. Date-time values must follow a consistent timezone policy. The implementation must define how timezone-naive values are handled or require timezone-aware values.
8. The request must not exceed the configured XML size limit.
9. Only authenticated users with the caterer role may create food listings.
10. XML parsing must reject DTD declarations and prevent external entity resolution.
11. The listing's initial availability status must be assigned by the server, not supplied by the client.
12. Client-supplied ownership information or listing identifiers must not be trusted.

Schema validation and application-level business-rule validation must remain separate.

### 9.5 Success Response

**HTTP Status:** `201 Created`

**Content-Type:** `application/xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<response>
    <status>success</status>
    <message>Food listing created successfully.</message>
    <data>
        <listing_id>123</listing_id>
    </data>
    <error/>
</response>
```

The listing identifier is assigned by the server after successful persistence. The example identifier is illustrative.

### 9.6 Error Responses

All errors must follow the standard XML response envelope defined in Section 3. The `data` element must be empty, and the `error` element must contain an error code and safe explanatory details.

| HTTP Status | Error Code | Condition |
|---|---|---|
| `400 Bad Request` | `MALFORMED_XML` | Request body is not well-formed XML |
| `401 Unauthorized` | `UNAUTHORIZED` | Authentication is missing or invalid |
| `403 Forbidden` | `FORBIDDEN` | Authenticated user lacks caterer permissions |
| `413 Content Too Large` | `PAYLOAD_TOO_LARGE` | Request exceeds the configured size limit |
| `415 Unsupported Media Type` | `VALIDATION_ERROR` | Request uses an unsupported content type |
| `422 Unprocessable Content` | `VALIDATION_ERROR` | XML fails schema validation or business-rule validation |
| `500 Internal Server Error` | `INTERNAL_ERROR` | Unexpected server-side failure |

For unsupported content types, the implementation should use a more specific error code such as `UNSUPPORTED_MEDIA_TYPE` if the shared error-code list is extended to include it.

Error responses must not expose stack traces, SQL queries, filesystem paths, credentials, internal exceptions, or other sensitive implementation details.

### 9.7 Implementation Status

This section defines the intended API contract. Authentication, database persistence, and the complete listing-creation workflow remain subject to implementation.

The listing must pass XML parsing, XSD validation, and business-rule validation before any database write occurs.