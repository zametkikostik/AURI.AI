const en = {
  appName: "AURI.AI",
  tagline: "Privacy-first AI Meeting Assistant",
  nav: {
    dashboard: "Dashboard",
    meetings: "Meetings",
    search: "Search",
    knowledge: "Knowledge",
    team: "Team",
    billing: "Billing",
    settings: "Settings",
    login: "Login",
    logout: "Logout",
  },
  common: {
    loading: "Loading…",
    save: "Save",
    cancel: "Cancel",
    search: "Search",
    language: "Language",
    error: "Something went wrong",
    noData: "No data",
  },
  dashboard: {
    title: "Dashboard",
    subtitle: "Overview of your meeting intelligence",
    recentMeetings: "Recent meetings",
    viewAll: "View all",
  },
  meetings: {
    title: "Meetings",
    new: "New meeting",
    empty: "No meetings yet",
    status: "Status",
    summary: "Executive summary",
    topics: "Topics",
    actionItems: "Action items",
    transcript: "Transcript",
    player: "Player & transcript",
    export: "Export",
  },
  search: {
    title: "Search",
    placeholder: "Search across all meetings…",
    hybrid: "Hybrid search",
    semantic: "Semantic",
    keyword: "Keyword",
  },
  knowledge: {
    title: "Knowledge Hub",
    subtitle: "Topics and decisions extracted from meetings",
  },
  team: {
    title: "Team",
    members: "Members",
    invites: "Pending invites",
    invite: "Send invite",
  },
  billing: {
    title: "Billing",
    plan: "Plan",
    upgrade: "Upgrade",
    manage: "Manage subscription",
  },
  settings: {
    title: "Settings",
    privacy: "Privacy / AI mode",
    notifications: "Notifications",
    saved: "Saved",
  },
  auth: {
    login: "Sign in",
    register: "Create account",
    email: "Email",
    password: "Password",
    orgName: "Organization name",
  },
  footer: {
    privacy: "Your meetings stay private by default",
  },
} as const;

export default en;
export type Dictionary = typeof en;
