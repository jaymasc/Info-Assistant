import { useMsal } from "@azure/msal-react";

export const useUserInfo = () => {
    const { accounts } = useMsal();

    if (accounts.length > 0) {
        return { name: accounts[0].name, isAuthenticated: true };
    }
    return { name: null, isAuthenticated: false };
};