export async function hasDocumentUploaderRole(accessToken: string): Promise<boolean> {
    const headers = new Headers();
    headers.append("Authorization", `Bearer ${accessToken}`);
    headers.append("Content-Type", "application/json");

    const documentUploaderRoleId = "<DOCUMENT_UPLOADER_ROLE_ID">;

    try {
        const response = await fetch("https://graph.microsoft.com/v1.0/me/appRoleAssignments", {
            method: "GET",
            headers: headers,
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        console.log("=====> DATA : ", data);

        // Ensure data.value exists and is an array
        if (!data.value || !Array.isArray(data.value)) {
            return false;
        }

        // Check if the user has the "DocumentUploader" role
        return data.value.some((assignment: { appRoleId: string }) => assignment.appRoleId === documentUploaderRoleId);
    } catch (error) {
        console.error("Error fetching user appRoleAssignments:", error);
        return false;
    }
}