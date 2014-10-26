# Celobox #

>This project is unstable. It is a work in progress. Actually, it's less than in progress. It's mostly just an idea with a few tests. Fair warning.

## Password Manifests ##

Celobox is a project to expose existing login and password change application endpoints as an implicit API.

The idea is to build manifests for existing web apps in order to allow second parties (such as a user running a password management app) to authenticate with the app and change their password, programmatically.

Eventually, I'm hoping that apps will publish their own manifests.

The beauty of this approach is that apps don't need to change. It's additive and passive. Win-win.
