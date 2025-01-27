import { PublicClientApplication, Configuration } from "@azure/msal-browser";
import { LogLevel } from "@azure/msal-browser";

export const msalConfig: Configuration = {
    auth: {
      clientId: "<APP_CLIENT_ID>", // Replace with your Azure AD App's client ID
      authority: "https://login.microsoftonline.com/<TENANT_ID>", // Replace with your tenant ID
      redirectUri: "http://localhost:5000", // Replace with your app's redirect URI
      postLogoutRedirectUri: "http://localhost:5000/#/", // TODO : Ensure this matches the post-logout redirect URI in Azure AD
    },
    cache: {
      cacheLocation: "sessionStorage", // or "localStorage"
      storeAuthStateInCookie: false,
    },
    system: {
      loggerOptions: {
        loggerCallback: (level, message, containsPii) => {
          if (containsPii) {
            return;
          }
          switch (level) {
            case LogLevel.Error:
              console.error(message);
              break;
            case LogLevel.Info:
              console.info(message);
              break;
            case LogLevel.Verbose:
              console.debug(message);
              break;
            case LogLevel.Warning:
              console.warn(message);
              break;
          }
        },
        piiLoggingEnabled: false,
        logLevel: LogLevel.Verbose,
      },
    },
  };

export const loginRequest = {
    scopes: ["User.Read"]
};