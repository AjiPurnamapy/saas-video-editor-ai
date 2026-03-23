// =============================================================================
// Constants
// =============================================================================

export const APP_NAME = "ClipForge AI";
export const APP_DESCRIPTION = "AI-powered video editing platform";

/** Password requirements displayed in the registration form */
export const PASSWORD_RULES = [
  "At least 8 characters",
  "At least one uppercase letter (A-Z)",
  "At least one lowercase letter (a-z)",
  "At least one digit (0-9)",
  "At least one special character (!@#$%^&*)",
];

/** Accepted video MIME types for upload */
export const ACCEPTED_VIDEO_TYPES = {
  "video/mp4": [".mp4"],
  "video/quicktime": [".mov"],
  "video/x-msvideo": [".avi"],
  "video/x-matroska": [".mkv"],
  "video/webm": [".webm"],
};
