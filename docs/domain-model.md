# Domain Model (###DRAFT###)

Here are the key points from the Domain Model document, keeping it casual:

**App Goals (The Big Picture):**

* **Main Goal:** Help photographers with their daily work and keep things organized.  
* **Two Sides to the Main Goal:**  
  1. Help run upcoming events smoothly using the app.  
  2. Provide tools to record and organize all the old stuff (past events) that happened before the app.  
* **Secondary Goal (The Smart Part):** Get enough data from all the activities and photos to generate cool Analytics. This helps users make better decisions, like picking the right camera settings or sorting out event conflicts. We'll be calculating trends and stuff.

**Notes on the "Stuff" (The Objects):**

* **Team/User (Photographers):**  
  * Pretty much everyone is a photographer for now.  
  * If you're on a Team, you only see your Team's data (like photos and events). This is how we handle Tenancy (data isolation).  
* **Camera:**  
  * The main way to capture an Image/Asset. Identified by a Camera ID (in the photo file) and possibly a Serial number.  
  * Can be swapped between photographers/events. The combo of Camera ID, Event, and Photographer helps figure out which physical camera was used.  
  * **Need to track usage\!** We need to know things like total shots, shutter mode, etc., to figure out when maintenance is due. We'll have to *guess* some counts because of deleted images (look at the largest gap in the image counter for an event).  
  * Other gear (like lenses) is important too\! We'll track usage and run analytics on that hardware.  
* **Event (Not just for Pros\!):**  
  * We call it Event instead of Job/Engagement to keep it open to hobbyists.  
  * Events can last multiple days, but each day/session needs its own calendar spot since attendance can change.  
  * Needs Attendees (from the User list).  
* **Category/Style:**  
  * Tells you what kind of photography it is: Sport, Wildlife, Portrait, etc.  
* **Organizers:**  
  * They set up the events.  
  * We'll rate them to help prioritize events if the schedule gets too busy.  
* **Venues/Location:**  
  * Where the events happen.  
  * We'll rate these too, maybe with sub-ratings for light, access, or available equipment.  
* **Performers:**  
  * The subjects of the photo shoot: airshow demos, models, wildlife.  
  * Not all events have them (like landscape photography).  
* **Trips:**  
  * Non-local events might need travel planning (which we'd link out to tools like TripIt).  
* **Deadlines:**  
  * Events can have due dates for the Workflow (e.g., for a customer or a competition submission).  
* **Albums:**  
  * Groups of images captured at an Event. Could be grouped by the entire Event or just by Session, depending on the photographer's choice.  
* **Pipelines & Workflow:**  
  * **Pipelines:** Define the steps (nodes) an image goes through (processing, branching, file outputs).  
  * **Workflow:** When you run a Pipeline on an Album.  
  * **Workflow Progress Tracking:** We track how far images have gotten in the Pipeline (furthest node, percentage of images reaching a node, overall completion percentage).  
  * We need a special "Termination" type for discarded images during the selection process.  
* **Collections (Physical Storage):**  
  * Where the actual Image/Asset files live. Can be local or remote.  
  * Ideally, a Collection only holds images for one Album, but reality is messy. We'll need a tool (Picker screen) to help users link images in a Collection back to their Album.  
  * Image files often get suffixes (e.g., from processing or all-numeric to differentiate versions). This can get confusing, and the photographer might need to manually sort out inconsistencies.  
  * We need to track when image files move between Collections (even if moved outside the app) so we don't lose the file's history.  
  * The app will eventually help users clean up and better organize old, archived Collections.  
* **Remote Connector:**  
  * A central place to store login details for remote storage services.  
  * Connectors to services other than storage (see TripIt) will be needed.
* **Images/Metadata:**  
  * Images have data like XMP sidecars and EXIF data.  
  * **Unique Image ID:** Camera ID \+ Counter \+ Image Timestamp helps identify a single image file.  
  * Reading metadata (which requires opening the file) can be costly for archived images. For archived stuff, we might just *guess* the timestamp based on the event date and ask the photographer for help to refine it.  
  * If we *can* get the metadata, we'll extract things like F-stop, ISO, and shutter speed for overall analytics. Sometimes reading it from one file in a group (like a JPG) is enough to apply to the whole group.  
* **Machine Learning (AI Stuff):**  
  * We'll use ML/AI to pull more data from the photos:  
    * Identify the subject (Performer/Model).  
    * Classify the photo type.  
    * Assess photo quality.  
    * Etc.  
* **Agents (Remote Workers):**  
  * Since the main app will be in the Cloud, we need local "Agents" to handle things that need access to physical storage (local or SMB Collections).  
  * Agents give the Cloud app access to these "non-local" Collections.  
  * Agents can also take over expensive, asynchronous jobs from the main Server to use local resources instead (see JobQueue).  
  * Agents are tied to a specific Photographer or Team/Tenant (they only process data for that person/team).