# Features Report

## Football Intelligence Dashboard

This report explains the new features added to the Football Intelligence project. The application is now organized as a single Flask-based dashboard with three main modules:

- **Part A: Player Tracking and Mapping**
- **Part B: Transfer Fee Prediction**
- **Part C: Event Detection**

The goal of these upgrades is to make the project easier to use, easier to present, and more useful for football analysis. The frontend was improved, the output reports were expanded, and new analysis views were added where the available data and APIs allow it.

---

## 1. Frontend and User Interface Improvements

### 1.1 Better Landing Dashboard

The landing page has been improved into a proper project dashboard. Instead of sending the user directly into one workflow, the home page now presents clear cards for each major part of the project.

The dashboard includes:

- A card for **Football Analysis / Part A**
- A card for **Transfer Fee Prediction / Part B**
- A card for **Event Detection / Part C**
- A recent history section for previously generated reports

This makes the project feel more like a complete application instead of a collection of separate scripts.

**Status:** Implemented  
**Main file:** `templates/index.html`

---

### 1.2 Cleaner Navigation Bar

The top navigation now gives direct access to all major pages:

- Dashboard
- Football Analysis
- Transfer Prediction
- Event Detection
- Admin
- Login / Logout

The active page is highlighted, so the user always knows which part of the application they are currently using.

**Status:** Implemented  
**Main file:** `templates/base.html`

---

### 1.3 Dark and Light Mode Toggle

A dark/light mode toggle has been added to the navigation bar. The selected theme is saved in the browser using local storage, so the user's preference remains active after refreshing the page.

This improves comfort during long usage sessions and gives the application a more polished feel.

**Status:** Implemented  
**Main files:** `templates/base.html`, `static/js/app.js`, `static/css/styles.css`

---

### 1.4 Loading Progress UI

The project already had progress handling for video analysis. The UI has now been improved further so transfer actions also show a loading state while processing.

For transfer actions, the page displays:

- A loading spinner
- A circular progress-style indicator
- Disabled submit button during processing

This prevents duplicate submissions and makes the application feel responsive even when the backend takes time.

**Status:** Implemented  
**Main files:** `templates/transfer.html`, `static/js/app.js`, `static/css/styles.css`

---

### 1.5 Improved Result Pages

The result pages now include more visual and structured output. Instead of showing only plain text or tables, the application now uses:

- Metric cards
- Badges
- Bar charts
- Line charts
- Radar charts
- Organized download buttons
- Tables for detailed output

This is especially useful in Part B, where model explanations, value trends, and market comparisons are easier to understand visually.

**Status:** Implemented  
**Main files:** `templates/football.html`, `templates/transfer.html`, `static/js/app.js`

---

### 1.6 Recent History Section

The application now saves a simple local history of generated outputs. This includes recent football analysis jobs, transfer reports, and event detection runs.

The history records:

- Module name
- Report title
- Short summary
- User name if logged in
- Date and time
- Related download files

This helps users quickly see what has already been generated.

**Status:** Implemented  
**Main file:** `app.py`  
**Storage file:** `static/outputs/analysis_history.json`

---

### 1.7 CSV and JSON Downloads

Part B reports are no longer limited to PDF only. The application now also generates:

- PDF report
- JSON report
- CSV report

This makes the output easier to reuse in spreadsheets, notebooks, presentations, or other applications.

**Status:** Implemented  
**Main file:** `app.py`

---

### 1.8 Responsive Mobile Layout

The CSS has been improved so the application works better on smaller screens. Grids collapse into single-column layouts, navigation becomes mobile-friendly, and result panels adjust to the available screen width.

This makes the dashboard usable on laptops, tablets, and mobile devices.

**Status:** Implemented  
**Main file:** `static/css/styles.css`

---

### 1.9 Toast Notifications

Flash messages are now also shown as toast notifications. This gives users a clearer success/error response after actions such as running analysis, generating transfer reports, or logging in.

**Status:** Implemented  
**Main files:** `templates/base.html`, `static/js/app.js`

---

### 1.10 Better PDF Report Design

The backend report generator creates structured PDF reports with sections instead of a single unorganized text dump. Reports now include clear headings, summaries, feature explanations, and generated time.

The PDF system is lightweight and does not require an external PDF library.

**Status:** Implemented  
**Main file:** `app.py`

---

## 2. Part A: Player Tracking and Mapping

Part A focuses on video-based football analysis. It uses the existing computer vision pipeline and now provides a better frontend experience, richer outputs, and additional movement statistics.

---

### 2.1 Upload Preview Before Processing

When a user selects a video file, the browser now shows a preview before processing starts. This helps users confirm they selected the correct video.

This is useful because football video processing can take several minutes, so previewing the input reduces mistakes.

**Status:** Implemented  
**Main files:** `templates/football.html`, `static/js/app.js`

---

### 2.2 Output Type Selection

The football analysis page now includes output selection controls. The user can choose which result sections they want to display after processing.

Available options include:

- Tracking video
- Pitch map / pitch video
- Stats report
- Movement heatmap

The backend still runs the main analysis pipeline, but the frontend uses these options to control which outputs are shown to the user after processing.

**Status:** Implemented as output display controls  
**Main files:** `templates/football.html`, `app.py`

---

### 2.3 Team Color Customization

Team color customization is a useful planned improvement for Part A. The current tracking pipeline automatically assigns teams using visual clustering. A future version can expose color selectors before processing so users can manually define Team 1 and Team 2 colors.

This feature would be valuable when automatic team assignment is not perfect due to lighting, similar kits, or camera quality.

**Status:** Planned / extendable  
**Reason:** Current pipeline uses automatic team assignment. Manual color input is not fully connected to the detection pipeline yet.

---

### 2.4 Player Heatmap Generation

The system now generates a movement heatmap from tracked pitch-coordinate positions. This heatmap gives a visual summary of where players spent the most time during the processed video.

The heatmap is created by collecting player coordinates over time, placing them on a pitch-like image, and applying a color overlay to show high-activity areas.

This helps answer questions such as:

- Which zones were used most?
- Was the game concentrated on one side?
- Did players occupy wide or central areas?

**Status:** Implemented  
**Main files:** `main_test.py`, `app.py`, `templates/football.html`

---

### 2.5 Ball Possession Percentage by Team

The project already had possession calculation logic, and the frontend now presents it more clearly. Possession is shown as a team percentage and is also available in TXT, CSV, and JSON formats.

The system estimates possession by assigning the ball to the closest relevant player and then mapping that player to a team.

**Status:** Implemented  
**Main files:** `main_test.py`, `templates/football.html`

---

### 2.6 Pass Detection and Pass Network Visualization

Pass detection is an advanced football analytics feature. The current project does not fully detect pass events using a dedicated pass model. However, the tracking CSV and possession data now provide a foundation for building pass detection later.

A future pass detector could identify:

- Ball movement from one player to another
- Change in possession player within the same team
- Direction and distance of pass
- Pass network between player IDs

**Status:** Planned / partially prepared  
**Reason:** Tracking data is now exported, but full pass detection logic is not implemented as a reliable event model.

---

### 2.7 Player Speed and Distance Covered

The tracking pipeline now records pitch-coordinate movement over time. From this movement, the system estimates:

- Distance covered in pitch units
- Average speed in pitch units per second
- Maximum speed in pitch units per second

These values are written into the statistics report. Since the pitch coordinate system is based on projected video positions, these are best treated as estimated football analytics values rather than official GPS-level measurements.

**Status:** Implemented  
**Main file:** `main_test.py`

---

### 2.8 Sprint Count and High-Intensity Run Detection

Sprint detection can be calculated from speed estimates by counting moments where a player's speed crosses a selected threshold.

The current implementation calculates speed and maximum speed, which gives the foundation for sprint detection. A future improvement can add a threshold-based sprint counter.

Example rule:

- Count a sprint when speed remains above a threshold for several consecutive frames.

**Status:** Prepared / future extension  
**Reason:** Speed data exists, but a dedicated sprint-count metric is not finalized yet.

---

### 2.9 Zone-Based Pitch Analysis

Zone-based analysis divides the pitch into areas such as defensive third, middle third, attacking third, left wing, center, and right wing. The current heatmap and tracking CSV provide the coordinate data needed for zone analysis.

A future version can use these coordinates to calculate:

- Time spent in each zone
- Team dominance by zone
- Ball activity by zone
- Player occupation by zone

**Status:** Prepared / future extension  
**Reason:** Coordinate output exists, but zone summaries are not yet shown as a dedicated table.

---

### 2.10 Mini-Map Animation Synced With Original Video

The pipeline generates a pitch movement video that acts like a mini-map. It shows player and ball positions on a pitch-style layout over time.

This gives users a tactical top-down view of movement alongside the processed match video.

**Status:** Implemented as pitch movement video  
**Main files:** `main_test.py`, `templates/football.html`

---

### 2.11 Event Detection in Part A

Event detection for shots, passes, tackles, and possession changes is a complex feature. Part A currently estimates possession changes through ball-to-player assignment, but it does not include a full local event detection model for shots, passes, or tackles.

Instead, event detection has been separated into Part C, where it can be handled through a hosted API only.

**Status:** Partially implemented for possession; full event detection moved to Part C  
**Reason:** The user requested no local event model for this feature.

---

### 2.12 Player ID Correction Tool

Player ID correction would allow the user to manually fix tracking ID swaps after processing. This is useful because object trackers can sometimes switch IDs when players overlap or move quickly.

The current project exports tracking data to CSV, which makes manual inspection possible, but an interactive correction tool has not been added yet.

**Status:** Planned / future extension  
**Reason:** Requires an interactive timeline editor and correction storage.

---

### 2.13 Exportable Match Statistics Report

Part A now exports statistics in multiple formats:

- TXT
- CSV
- JSON
- Tracking CSV
- Heatmap image
- Processed video
- Pitch movement video
- Pitch map image

This makes the analysis output easier to use in reports and presentations.

**Status:** Implemented  
**Main files:** `app.py`, `templates/football.html`

---

### 2.14 Support for Multiple Video Formats

The application accepts common football video formats:

- MP4
- MOV
- AVI
- MKV
- WEBM

If a user uploads an unsupported file type, the application shows a clear error message.

**Status:** Implemented  
**Main file:** `app.py`

---

### 2.15 Before/After Sample Demo Video

A sample demo mode is a useful presentation feature because it lets users test the app without uploading a new video. The current project has previous uploaded and generated videos inside the static outputs folder, but a dedicated one-click demo button has not been fully added to the UI.

**Status:** Planned / future extension  
**Reason:** Existing sample outputs are available, but no formal demo workflow is connected yet.

---

## 3. Part B: Transfer Fee Prediction

Part B predicts and explains football transfer values using the transfer dataset and saved machine learning models. The new changes make the prediction output easier to understand and more useful for decision-making.

---

### 3.1 Confidence Range for Predicted Fee

Predictions now include a confidence range instead of showing only one fixed value.

Example:

`EUR 60M - EUR 75M`

This is useful because transfer fees are uncertain in real life. The range communicates that the prediction is an estimate, not an exact market truth.

The margin becomes wider if the app had to fall back from a requested model.

**Status:** Implemented  
**Main file:** `app.py`

---

### 3.2 Explanation Chart for Price Factors

The prediction result now includes a chart showing how different pricing factors affect the final estimate.

Factors can include:

- Age factor
- League tier factor
- Buying club premium
- International factor
- Performance factor
- Contract urgency

This makes the model explanation easier to understand for users who do not want to read a long table.

**Status:** Implemented  
**Main files:** `app.py`, `templates/transfer.html`, `static/js/app.js`

---

### 3.3 Model Selector With Availability Status

The transfer form includes model selection. The user can choose between:

- XGBoost
- Random Forest
- Neural Network

The application also checks whether model files exist and whether the XGBoost dependency is available.

**Status:** Implemented  
**Main files:** `app.py`, `templates/transfer.html`

---

### 3.4 Automatic Fallback Model Label

Previously, selecting XGBoost could fail if the `xgboost` package was missing. The model loading logic now handles this more safely.

If the requested model cannot be loaded, the system falls back to another available model or the formula-based fallback. The result also shows which model was actually used.

This prevents the transfer workflow from crashing due to an optional dependency.

**Status:** Implemented  
**Main file:** `Part b Players Transfer Fee Prediction/src/predictor.py`

---

### 3.5 Similar Past Transfers

The prediction page now shows similar historical transfers. These are selected by comparing the predicted fee with real transfer fees from the transfer dataset.

The table includes:

- Player
- From club
- To club
- Fee
- Season

This gives the user market context and helps validate whether the predicted fee feels realistic.

**Status:** Implemented  
**Main file:** `app.py`

---

### 3.6 Player Market Value Trend Chart

For selected players, the system reads historical valuation data and displays a market value trend chart.

This helps users understand whether a player has been rising, declining, or remaining stable in market value.

**Status:** Implemented  
**Main files:** `app.py`, `templates/transfer.html`

---

### 3.7 Age vs Value Curve

The market insights page includes an age-value curve. Players are grouped into age categories such as rising, peak, declining, and older age brackets.

This helps show how football market value usually changes with age.

**Status:** Implemented in market insights  
**Main files:** `market_insights.py`, `app.py`, `templates/transfer.html`

---

### 3.8 Predicted Fee vs Current Market Value

The prediction result now compares the predicted transfer fee with the player's current market value. This helps identify whether the predicted transfer would be above or below current valuation.

This is useful for spotting:

- Overpriced transfers
- Potential bargains
- Premiums caused by club demand or player profile

**Status:** Implemented  
**Main file:** `app.py`

---

### 3.9 Transfer Affordability Check

The transfer prediction form now allows users to enter a club budget in EUR millions. The result tells whether the predicted fee is affordable or over budget.

Example outputs:

- Affordable with EUR 10M remaining
- Over budget by EUR 15M

This makes the prediction more practical for club-style decision-making.

**Status:** Implemented  
**Main files:** `app.py`, `templates/transfer.html`

---

### 3.10 Wage Prediction and Yearly Salary Estimate

The system now estimates wages from the predicted transfer fee. In transfer simulations, it also shows yearly salary estimate.

The wage calculation is simple and should be understood as an estimate, not a real contract prediction.

**Status:** Implemented  
**Main file:** `app.py`

---

### 3.11 Contract Length Impact Simulator

Contract information already influences the formula-based transfer calculation through contract urgency. However, a full interactive contract length slider has not been added yet.

A future version can allow the user to manually adjust contract years and immediately see how the predicted value changes.

**Status:** Partially implemented through pricing formula; interactive simulator planned

---

### 3.12 Shortlist Builder

A shortlist builder would allow users to save multiple players and compare them later. The current application saves generated reports in history, but it does not yet include a dedicated player shortlist interface.

**Status:** Planned / future extension

---

### 3.13 Best Alternatives Under a Budget

The advanced filter and market data can support budget-based recommendations. The current app can filter players and check affordability, but a dedicated "best alternatives under budget" workflow is not yet fully built.

**Status:** Partially supported through advanced filter; dedicated recommendation view planned

---

### 3.14 Squad Fit Score for Buying Club

Squad fit score would estimate how suitable a player is for a buying club based on position, club strength, role, league, and budget. The current system includes buying club premium and club context, but it does not yet calculate a separate squad fit score.

**Status:** Planned / future extension

---

### 3.15 Risk Score

A transfer risk score could combine:

- Age risk
- Value risk
- Contract risk
- Performance risk
- Injury risk if injury data is available

The current project includes some of these signals, such as age, value, performance, and contract information. Injury data is not currently available in the dataset.

**Status:** Partially prepared; full risk score planned

---

### 3.16 Future Resale Value Prediction

The future performance workflow estimates player trajectory across future seasons. A dedicated resale value prediction is not yet separated as its own feature.

This could be added later by combining age curve, current value, performance trend, and contract assumptions.

**Status:** Partially supported through future performance prediction; dedicated resale feature planned

---

### 3.17 Top Undervalued Players Recommendation

The market insights workflow now identifies undervalued players by comparing rule-based estimated value with current market value.

This helps users find players who may be worth more than their current valuation suggests.

**Status:** Implemented  
**Main files:** `market_insights.py`, `app.py`, `templates/transfer.html`

---

### 3.18 League-Wise and Position-Wise Market Charts

The market page now includes visual charts for market distribution. Position-wise value distribution is implemented directly, and age/value distribution is also shown.

League-wise analysis can be expanded further using the existing league data in the dataset.

**Status:** Position-wise implemented; league-wise extendable  
**Main files:** `app.py`, `templates/transfer.html`

---

### 3.19 Player Radar Chart

The prediction result includes a radar chart for player profile indicators such as:

- Goals
- Assists
- Minutes
- International caps
- Current value
- Age profile

This gives a quick visual overview of the selected player's profile.

**Status:** Implemented  
**Main files:** `app.py`, `templates/transfer.html`, `static/js/app.js`

---

### 3.20 Export Report for Simulated Transfer

Transfer simulation results now use the same export system as other transfer actions. The user can download simulation output as:

- PDF
- CSV
- JSON

**Status:** Implemented  
**Main file:** `app.py`

---

## 4. Part C: Event Detection

Part C was added as a separate module named **Event Detection**. This module follows the requirement that event detection should use an API only and should not add a local model.

---

### 4.1 API-Only Event Detection

The Event Detection page allows the user to upload an image or video. If a video is uploaded, the system samples frames from the video and sends those frames to a hosted API.

The module is designed to detect football events such as:

- Goals
- Yellow cards
- Red cards
- Shots
- Passes
- Tackles
- Possession changes

The API response is filtered for supported football event labels.

**Status:** Implemented as API-only workflow  
**Main files:** `templates/events.html`, `app.py`

---

### 4.2 No Local Event Model

No local event detection model was added to the project. This keeps the implementation aligned with the requirement that Part C should only work through a free/API-based service if available.

The app expects environment variables for configuration:

- `EVENT_DETECTION_API_KEY`
- `EVENT_DETECTION_MODEL_ID`
- Optional: `EVENT_DETECTION_API_URL`

If these are not configured, the page clearly reports that event detection is unavailable.

**Status:** Implemented correctly according to project requirement

---

### 4.3 Event Detection Output

When the API returns detections, the app displays:

- Summary metrics
- Event count chart
- Detection table
- Frame name
- Event label
- Confidence
- X/Y location

The output can also be downloaded as:

- PDF
- CSV
- JSON

**Status:** Implemented  
**Main files:** `app.py`, `templates/events.html`

---

## 5. Admin and Local User Features

### 5.1 Lightweight Login

A simple local login system was added. It is not meant to be production authentication, but it allows generated history to be associated with a username.

This is useful for a university project because it gives the application a multi-user feel without adding database complexity.

**Status:** Implemented  
**Main files:** `templates/login.html`, `app.py`

---

### 5.2 Admin Page

The admin page gives visibility into important project files.

It shows:

- Transfer CSV datasets
- Saved model files
- Recent output files
- Event API configuration status
- Model availability status

This helps with debugging and presentation because the user can quickly confirm that the required datasets and model files exist.

**Status:** Implemented  
**Main files:** `templates/admin.html`, `app.py`

---

## 6. Export and Reporting System

The project now has a broader reporting system. Outputs are saved into the `static/outputs` folder and can be downloaded directly from the browser.

Supported exports include:

- PDF reports
- CSV reports
- JSON reports
- Processed videos
- Pitch movement videos
- Pitch map images
- Movement heatmaps
- Tracking CSV files

This is important because analysis is only useful if the results can be shared, reviewed, and reused later.

**Status:** Implemented  
**Main file:** `app.py`

---

## 7. Technical Summary

### Frontend Technologies

- HTML templates using Jinja
- CSS for responsive layout and dark/light mode
- JavaScript for theme handling, charts, loading states, previews, and autocomplete

### Backend Technologies

- Flask
- Python
- CSV/JSON/PDF output generation
- Existing transfer prediction package
- Existing football tracking pipeline
- API-based event detection workflow

### Important Files

- `app.py`
- `templates/base.html`
- `templates/index.html`
- `templates/football.html`
- `templates/transfer.html`
- `templates/events.html`
- `templates/admin.html`
- `templates/login.html`
- `static/css/styles.css`
- `static/js/app.js`
- `Part a Player Tracking And Mapping/football-analysis-CV-main/local_exec/main_test.py`
- `Part a Player Tracking And Mapping/football-analysis-CV-main/local_exec/config/config.py`
- `Part b Players Transfer Fee Prediction/src/predictor.py`

---

## 8. Overall Impact

These improvements turn the project from a basic Flask wrapper into a more complete football intelligence application.

The frontend is now easier to navigate, more visual, and more user-friendly. Part A now provides richer video analysis outputs, including heatmaps and tracking exports. Part B now explains transfer predictions with confidence ranges, charts, trends, affordability checks, and similar transfers. Part C adds a clean API-only approach for event detection without adding any local model.

Overall, the project is now stronger for demonstration, reporting, and practical football analysis.

