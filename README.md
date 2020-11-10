# User Information Service (UIS)

Python (Flask) RESTful API service for managing FABRIC user information.

# About

UIS manages information about known FABRIC users - their portal preferences, SSH public keys, alternate
identities (ORCID, Web of Science etc), publications etc. Basic information about users comes from 
CILogon/COmanage (name, email etc) while the rest is stored in the associated persistent relational database.

UIS design is modeled after [Project Registry](https://github.com/fabric-testbed/project-registry/blob/master/README.md).
Authentication is performed via CILogon/VouchProxy, and much of the information about the user can only be
retrieved by the user herself. 

UIS is  implemented as a RESTful service using OpenAPI 3.0 (Swagger) definition and is intended to be deployed
as a Dockerized Flask application run by `uwsgi` behind dedicated Nginx (Sample [Nginx config](nginx)).

# API Specification
 
UIS provides guarded access to user information - portal preferences, publications, SSH keys, alternate IDs and so on.

Most of the API calls allow only the user herself to request her own information and is intended (via
mechanism like [VouchProxy](https://github.com/vouch/vouch-proxy)) to allow a user to authenticate via 
a portal application and, once authenticated, for the portal to request the necessary information on 
user behalf

The initial implementation provides several entrypoints:

### Version

The project registry API is versioned based on the release found in GitHub.

API `version`:

Resource | Action | Input | Output
:--------|:----:|:---:|:---:
`/version` | GET: current API version | NA | Version format

Example: Version format

```json
{
  "gitsha1": "Release SHA as string",
  "version": "Release version as string"
}
```

## People

Provides the ability to search known users. Information provided about users is 
(this information is considered public) and can be invoked by any authenticated user:


API `/people`:

| Resource | Action | Input | Output |
:--------|:----:|:---:|:---:
`/people` | GET: list of all people | `person_name` optional query parameter, `X-PageNo` optional header parameter | Array of People Short format (25 per page)

Returns a People_Short structure:
```
uuid:
  type: string
name:
  type: string
email:
  type: string
```

## Preferences

Intended for the portal to store and retrieve different types of preferences. 
Only returned to the user herself. These are opaque strings to UIS and are encoded and interpreted 
by the portal logic. Preferences come in three separate flavors: `settings` for portal settings,
`permissions` - for personal information visibility permissions and `interests` - for social interests 
(to enable e.g. to 'follow' projects).

| Resource | Action | Input | Output |
:--------|:----:|:---:|:---:
| /preferences/{preftype}/{uuid} | GET: get specific type of preference | preference type and uuid of the user | JSON string encoding preferences |
| /preferences/{preftype}/{uuid} | PUT: update specific type of preference | preference type and uuid of the user| Updated value of the preference |
| /preferences/{uuid} | GET: get all preferences as an object | uuid of the user | JSON structure containing all preferences |

The `/preferences/{uuid}` call returns a Preferences structure:
```
Preferences:
   properties:
     settings:
       type: object
     permissions:
       type: object
     interests:
       type: object
```

# Database

Uses postgres. 

# Testing

Setup your env_template, source it. Then run `docker-compose --env-file env-template up`. 

Once the containers are up connect to `http://localhost:5000/ui` to interact with the service. 

# Deployment

The application is intended to be Dockerized (see [Dockerfile](Dockerfile)) and deployed together with Nginx and VouchProxy
(see [docker-compose.yml](docker-compose-nginx.yml) and [Nginx configuration](nginx/)). 

# References

- Swagger: [https://swagger.io](https://swagger.io)
- OpenAPI Specification: [https://swagger.io/docs/specification/about/](https://swagger.io/docs/specification/about/)
- CILogon: [https://www.cilogon.org](https://www.cilogon.org)
- COmanage: [https://www.cilogon.org/comanage](https://www.cilogon.org/comanage)
- VouchProxy: [https://github.com/vouch/vouch-proxy](https://github.com/vouch/vouch-proxy)
