# Tøyenbadet for Home Assistant

Custom integration for keeping eye on the capacity at Tøyenbadet.

## Opening hours

The device includes a read-only ticket-sales calendar, a **Ticket sales open**
status, and **Next ticket-sales opening/closing** timestamp sensors. The calendar
works with Home Assistant's built-in calendar card and calendar automation
triggers. See the [dashboard example](examples/opening-hours-dashboard.yaml).
Replace its entity IDs with those assigned in your installation.

Hours come from the structured schedule embedded in
[Oslo kommune's page](https://www.oslo.kommune.no/natur-kultur-og-fritid/svommehaller-i-oslo/toyenbadet/).
The integration fetches it hourly, independently of visitor counts, and updates
its time-dependent states locally each minute. Times use `Europe/Oslo`, including
daylight-saving changes. Next opening means the next future opening, even while
currently open; next closing includes the current interval's closing time.

These are scheduled **ticket-sales** hours, not a guarantee of admission. The
page states that the pool closes 30 minutes later and changing rooms one hour
later. Calendar descriptions include this information and published daily notes.

Only published dates are used; no weekly recurrence is guessed. Closed days have
no opening events. Missing dates or website failures make the hours entities
unavailable while visitor counts continue to work. A missing future timestamp
is unknown. The calendar's horizon is limited to the dates provided by the
website (currently six weeks). Its HTML format is not a documented API, so a
website change may require an integration update.
