import { useEffect, useState } from "react";

export const useEasyAuthUser = () => {
    const [userInfo, setUserInfo] = useState({ name: null, canUploadDocuments: false, isAuthenticated: false });

    useEffect(() => {
        const fetchUserInfo = async () => {
            try {
                const response = await fetch("/.auth/me");
                if (!response.ok) {
                    throw new Error(`Error fetching user info: ${response.status}`);
                }
                const data = await response.json();
                
                if (!data || data.length === 0) return;
                
                console.log("=====> Data : ", data);

                const user = data[0]; // Get the authenticated user
                const name = user.user_id || "Unknown User";

                // Extract roles from user_claims array
                const rolesClaim = user.user_claims?.find((claim: { typ: string; }) => claim.typ === "roles");
                const roles = rolesClaim ? (Array.isArray(rolesClaim.val) ? rolesClaim.val : [rolesClaim.val]) : [];

                // Check if "documentUploader" is in the roles
                const canUploadDocuments = roles.includes("documentUploader");

                setUserInfo({ name, canUploadDocuments, isAuthenticated: true });
            } catch (error) {
                console.error("Error fetching user info:", error);
                setUserInfo({ name: null, canUploadDocuments: false, isAuthenticated: false });
            }
        };

        fetchUserInfo();
    }, []);

    return userInfo;
};