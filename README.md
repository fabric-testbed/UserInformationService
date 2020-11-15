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

![UIService API](imgs/api-screenshot.png)

Intended for the portal to store and retrieve different types of preferences. 
Only returned to the user herself. These are opaque strings to UIS and are encoded and interpreted 
by the portal logic. Preferences come in three separate flavors: `settings` for portal settings,
`permissions` - for personal information visibility permissions and `interests` - for social interests 
(to enable e.g. to 'follow' projects).

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

Uses postgres. Schema is defined via ORM under
[server/swagger_server/database/models.py](server/swagger_server/database/models.py)

# Testing

Setup your env_template. Then run `docker-compose -f <compose file> --env-file <env file> up`.

Copy and edit [env_template](env_template) to customize env file for specific type of test.  

There are multiple ways to test with different arrangements of containers:
- [Simple 'no-Nginx' setup](docker-compose-nonginx.yml), in which just two dockers are stood up. Typically used for 
basic testing without any authentication. Once the containers are up connect to `http://localhost:5000/ui` to 
interact with the service.
    - API server (under uWSGI)
    - Postgres
- ['Vouch Proxy' local](docker-compose.yml), configured to run on localhost, adds containers for. Used for
testing proper authentication with CILogon, albeit from localhost only and using provided [self-signed SSL certs](ssl/). 
Once the containers are up connect to https://127.0.0.1:8443/ui to interact with the service (please not not to use 
`localhost`) 
    - Nginx
    - API Server
    - Vouch Proxy
    - Postgres 

# Deployment

Copy [vouch/config_template](vouch/config_template) to `vouch/config`, edit at least the following parameters:
- `vouch/publicAccess` set to `false` (unless testing)
- `jwt/secret` must be changed - if using in production, it likely needs to be the same as on all other services,
e.g. Project Registry
- `cookie/domain` must be set to appropraite domain
- `oauth/client_id` and `oauth/client_secret` must match those issued to this service in CI Logon as OIDC client
- `oauth/callback_url` must match the callback URL set in CI Logon

# References

- Swagger: [https://swagger.io](https://swagger.io)
- OpenAPI Specification: [https://swagger.io/docs/specification/about/](https://swagger.io/docs/specification/about/)
- CILogon: [https://www.cilogon.org](https://www.cilogon.org)
- COmanage: [https://www.cilogon.org/comanage](https://www.cilogon.org/comanage)
- VouchProxy: [https://github.com/vouch/vouch-proxy](https://github.com/vouch/vouch-proxy)
