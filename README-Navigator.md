# Steps to deploy Non Secure-Mode version

Login to Azure, follow steps, select correct azure env for the deployment
> az login

Create a working version of local.env
> cp scripts/environments/local.env.example scripts/environments/local.env

Fill out the starter fields:

export LOCATION="eastus" # Required
export WORKSPACE="infoasst-pbuck-test-2025-04-10-2" # Required (example of my naming convention)
export SUBSCRIPTION_ID="Paste Subscription ID here" # Required

Start deployment command:
> make deploy

After about about a minute, answer with 'y' at the prompt:
> Are you happy with the plan, would you like to apply? (y/N)

Deployment should complete in around 25 minutes

It's possible to get status 400 errors that look like this:
Deployment Name: "gpt-35-turbo-16k"): performing CreateOrUpdate: unexpected status 400 (400 Bad Request) with error: InsufficientQuota: This operation require 240 new capacity in quota

I've fixed those by lowering the capacity way down in the local.env file.  I'm not sure what balance to set but I've been using low values:
export AZURE_OPENAI_CHATGPT_MODEL_CAPACITY="10" # Required
export AZURE_OPENAI_EMBEDDINGS_MODEL_CAPACITY="10" # Required

After deployment succeeds, find the deployment on the Azure portal under Home > Resource groups:
https://portal.azure.com/#browse/resourcegroups

Tap on the link to the new infoasst- deployment, look for the infoasst-web-xxxxx resource and tap on it
Observe the 'Health Check' count.  It might be less than 100% or even 0%.  In general, it can take around 15 minutes to reach 100%
There may be times when the assigned servers are 'bad' and the system will auto replace them after around 15 minutes of bad health.

Copy the 'Default domain' link and open it in a private browser page 
(it will look something like this after you add https : https://infoasst-web-ldlye.azurewebsites.net)

You'll have to login and accept permissions

# Steps to access the 'Manage Content' link in the app

We made changes to the app to only show 'Manage Content' to users with app role of 'documentUploader'
To view that option, follow these steps:

Navigate to the Azure Portal > Microsoft Entra ID > App registrations
https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/~/RegisteredApps

Tap twice on the 'Created on' column title to sort the newly deployed registrations to the top
Look for a registration named like : infoasst_web_access_xxxxx
On the left menu navigate to : Manage > App roles
In the main content, tap on : 'How do I assign app roles'
A right side popup titled 'Assigning app roles' will appear.  Tap on the 'Enterprise Applications' blue link (inside a text paragraph)
On the left menu navigate to : Manage > Users and Groups
In the main content, at top left, tap on : '+ Add user/group'
On left side, under 'Users and Groups', tap on the 'None Selected' blue link
In the 'Users and Groups' popup, search for your email name
Check the box next to your name and press the 'Select' button at bottom
After the search popup disappears, at bottom left, tap on the 'Assign' button
You should now see a list with your name showing a role assignment of 'documentUploader'
 
After that, I recommend closing the browser window showing the Navigator app and logging in again in a new window.
If you don't see the Manage Content link, wait a minute and refresh the screen.
I've seen this link vanish at times after navigating around the app but it generally returns if you refresh a few times.

# Running the batch tests

Make sure to load some documents into Navigator
Make sure you have an excel file with columns titled 'question' and 'answer' filled with questions relevant to the loaded docs

The test script expects the questions file to be at the following location in the code:
app/backend/test_data/question-answer.xlsx

The checked-in version is currently just a few test questions about a test file I use.  
You should replace that file with the one that has your questions and give it the same name.
If you want to use a different name, you can edit the script code at app/backend/evaluation_suite.py :

    file_path = "./test_data/question-answer.xlsx"


There is a need to add an OPENAI_API_VERSION environment variable for the script to use:

    In the code, find this file : scripts/environments/infrastructure.debug.env
    At the bottom of that file, add a line like this : AZURE_OPENAI_API_VERSION="2024-02-01"

There is also a need to place AZURE-OPENAI-API-KEY in the key vault:

    Navigate to the deployed resources via Azure portal
    Locate and tap the infoasst-aoai-xxxxx resource
    On the left menu navigate to : Resource management > Keys & endpoint
    You will see fields named 'Key 1' and 'Key 2' ; tap the right 'copy to clipboard' icon next to one of the fields
    Navigate back to the deployed resources, locate and tap on infoasst-kv-xxxxx
    On the left menu navigate to : Objects > Secrets
    At the top, tap on '+ Generate/Import'
    Paste the key that was copied into the clipboard into the field named 'Value'
    In the 'Name' field type : 'AZURE-OPENAI-API-KEY'
    Press the 'Create' button at the bottom left of the screen ; key should now show up in the list of secrets

Before running the script, you have to setup a virtual env and install the requirements:

> python -m venv .venv
> source .venv/bin/activate
> pip install -r app/backend/requirements.txt

Now you can run the test script:

> python -s app/backend/evaluation_suite.py 

After a few moments, it will start printing logs of questions, answers, contexts
At the end of the run, it will print out the resulting metrics which currently look something like this:

Evaluation Metrics:
Context Precision Score: 0.75
Context Recall Score: 0.75
Faithfulness Score: 0.96
True Positives (TP): 3
False Positives (FP): 1
False Negatives (FN): 1
Balanced Accuracy (Fowlkes-Mallows Index): 0.75

# Steps to deploy Secure-Mode version

Update the WORKSPACE value in local.env to something different than the last deployment and maybe named to indicate secure-mode

    export WORKSPACE="infoasst-pbuck-test-2025-04-10-3-secure" # Required (example of my naming convention)

Specify secure-mode in local.env

    export SECURE_MODE=true

The secure-mode deployment will have two phases.  For the first phase, we just run 'make deploy' as normal:

> make deploy

After about about a minute, answer with 'y' at the prompt:
> Are you happy with the plan, would you like to apply? (y/N)

Deployment should complete in around xx minutes

It's possible to get status 400 errors relating to some private endpoint.  This seems to be just a communication error.
If this happens, I go to the portal, delete the deployment and try again.  It generally works at the second attempt.

At the end of the first phase, the process will present you with the following command line prompt:

    Connection from the client machine to the Information Assistant virtual network is required to continue the deployment.
    Please configure your connectivity and ensure you are using the DNS resolver at 10.0.8.180

    Are you ready to continue (y/n)?

Before saying 'yes', it will be necessary to modify three resources to allow them to receive public connections.
After the deployment is finished, you should reverse the following steps and make those resources only privately accessible again.

Make Key Vault networking public:
On the portal, find the key vault (infoasst-kv-xxxxx ) , settings/networking section and set 'Allow public access from all networks' then tap 'Apply'

Make Container Registry resource public:
On the portal, search for the resource of type 'container registry', in Settings/Networking set access to ‘All networks’ then tap 'Save'

Make Search Service public:
On the portal, search for the resource of type 'search service', in Settings/Networking set access to 'All networks' then tap 'Save'.  
For this one, wait until the blue 'Updating' state goes away (a couple of minutes)


After making those networking changes, you can tap 'y' to allow the deployment to continue onto the second phase
