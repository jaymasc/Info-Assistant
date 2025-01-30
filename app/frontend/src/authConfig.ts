import { config } from "./authConfig.generated"

import { PublicClientApplication, Configuration } from "@azure/msal-browser";
import { LogLevel } from "@azure/msal-browser";

export const msalConfig: Configuration = {
    auth: {
      clientId: config.clientId, 
      authority: `https://login.microsoftonline.com/${config.tenantId}`, 
      redirectUri: config.redirectUri,
      postLogoutRedirectUri: config.redirectUri,
    },
    cache: {
      cacheLocation: "sessionStorage",
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


