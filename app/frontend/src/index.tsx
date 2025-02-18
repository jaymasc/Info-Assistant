// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { HashRouter, Routes, Route } from "react-router-dom";
import { initializeIcons } from "@fluentui/react";

import "./index.css";

import { Layout } from "./pages/layout/Layout";
import NoPage from "./pages/NoPage";
import Chat from "./pages/chat/Chat";
import Content from "./pages/content/Content";
import Tutor from "./pages/tutor/Tutor";
import { Tda } from "./pages/tda/Tda";
import { useEasyAuthUser } from "./useEasyAuthUser";

initializeIcons();

export default function App() {
    const userInfo = useEasyAuthUser();  // Fetch user info via Easy Auth

    if (!userInfo.isAuthenticated) {
        return <div>Loading...</div>; // Optionally add a loading state
    }

    return (
        <div className="App">
            <HashRouter>
                <Routes>
                    <Route path="/" element={<Layout showContentNav={userInfo.canUploadDocuments} />}>
                        <Route index element={<Chat />} />
                        <Route path="content" element={<Content />} />
                        <Route path="*" element={<NoPage />} />
                        <Route path="tutor" element={<Tutor />} />
                        <Route path="tda" element={<Tda folderPath={""} tags={[]} />} />
                    </Route>
                </Routes>
            </HashRouter>
        </div>
    );
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>
);