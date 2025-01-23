// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

import React, {useEffect,  useState}  from 'react';
import ReactDOM from "react-dom/client";
import { HashRouter, Routes, Route } from "react-router-dom";
import { initializeIcons } from "@fluentui/react";

import { PublicClientApplication } from "@azure/msal-browser";
import { MsalProvider } from "@azure/msal-react";
import { msalConfig } from "./authConfig";
import { useUserInfo } from "./useUserInfo";
import { loginRequest } from './authConfig';
import { callMsGraph } from './graph';

import { AuthenticatedTemplate, UnauthenticatedTemplate, useMsal } from '@azure/msal-react';
import { SignInButton } from './SignInButton';

import "./index.css";

import { Layout } from "./pages/layout/Layout";
import NoPage from "./pages/NoPage";
import Chat from "./pages/chat/Chat";
import Content from "./pages/content/Content";
import Tutor from "./pages/tutor/Tutor";
import { Tda } from "./pages/tda/Tda";

initializeIcons();

const msalInstance = new PublicClientApplication(msalConfig);

export const fetchUserInfoAndRoles = () => {

    console.log("=====> Inside PublicClientApplication before useMsal");

    const { instance, accounts } = useMsal();

    console.log("=====> Inside PublicClientApplication after useMsal");

    if (accounts.length === 0) {
        console.log("=====> No accounts found.");
        return;
    } else {
        console.log("=====> Account Name: ", accounts[0].name)
    }
};

export default function App() {
    const userInfo = useUserInfo();
    const [toggle, setToggle] = React.useState('Work');

    useEffect(() => {
        msalInstance.initialize().then(() => {
            msalInstance.handleRedirectPromise()
                .then((response) => {
                    if (response) {
                        // Handle successful response
                        console.log("=====> Login successful", response);
                        console.log("=====> Account Name: ", userInfo.name);
                    }
                })
                .catch((error) => {
                    console.error("=====> Login error", error);
                });
        }).catch((error) => {
            console.error("=====> MSAL Initialization error", error);
        });
    }, [userInfo]);

    return (
        <div className="App">
            <AuthenticatedTemplate>
                <HashRouter>
                <Routes>
                    <Route path="/" element={<Layout />}>
                        <Route index element={<Chat />} />
                        <Route path="content" element={<Content />} />
                        <Route path="*" element={<NoPage />} />
                        <Route path="tutor" element={<Tutor />} />
                        <Route path="tda" element={<Tda folderPath={""} tags={[]} />} />
                    </Route>
                </Routes>
                </HashRouter>    
            </AuthenticatedTemplate>

            <UnauthenticatedTemplate>
                <SignInButton />
            </UnauthenticatedTemplate>
        </div>
    );
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
        <MsalProvider instance={msalInstance}>
            <App />
        </MsalProvider>
    </React.StrictMode>
);