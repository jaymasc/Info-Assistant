import { useMsal } from "@azure/msal-react";
import { hasDocumentUploaderRole } from "./graph";  // Ensure this function returns a boolean
import { useEffect, useState } from "react";

export const useUserInfo = () => {
    const { accounts, instance } = useMsal();
    const [canUploadDocuments, setCanUploadDocuments] = useState<boolean>(false);

    useEffect(() => {
        const checkUploadPermission = async () => {
            if (accounts.length > 0) {
                try {
                    const tokenRequest = {
                        scopes: ["https://graph.microsoft.com/.default"],
                        account: accounts[0],
                    };
                    const response = await instance.acquireTokenSilent(tokenRequest);
                    const hasPermission = await hasDocumentUploaderRole(response.accessToken);
                    setCanUploadDocuments(hasPermission);
                } catch (error) {
                    console.error("Error checking document upload permission:", error);
                }
            }
        };

        checkUploadPermission();
    }, [accounts, instance]);

    if (accounts.length > 0) {
        return { name: accounts[0].name, canUploadDocuments, isAuthenticated: true };
    }
    return { name: null, canUploadDocuments: false, isAuthenticated: false };
};

