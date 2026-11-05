/* A compact consistent 24x24 line icon set for FriendsMeeting. */
const paths = {
  "message-circle": '<path d="M7.9 20A9 9 0 1 1 20 12c0 4.4-3.6 8-8 8H6l1.9-3.8"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  settings: '<path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"/><path d="M19.4 15.1 21 16l-2 3.5-1.8-.9a8 8 0 0 1-2.2 1.3L14.7 22h-4l-.3-2.1a8 8 0 0 1-2.2-1.3l-1.8.9-2-3.5 1.6-.9a8 8 0 0 1 0-2.6L4.4 11l2-3.5 1.8.9a8 8 0 0 1 2.2-1.3L10.7 5h4l.3 2.1a8 8 0 0 1 2.2 1.3l1.8-.9 2 3.5-1.6.9a8 8 0 0 1 0 3.2Z" transform="translate(0 -1)"/>',
  send: '<path d="m22 2-7 20-4-9-9-4 20-7ZM22 2 11 13"/>',
  check: '<path d="m5 12.5 4.5 4.5L20 6"/>',
  "check-double": '<path d="m3 12.5 4 4L17 6"/><path d="m9 12.5 4 4L23 6"/>',
  "arrow-left": '<path d="m12 19-7-7 7-7M19 12H5"/>',
  refresh: '<path d="M20 11a8 8 0 0 0-14-5L3 9m0-6v6h6M4 13a8 8 0 0 0 14 5l3-3m0 6v-6h-6"/>',
  "chevron-down": '<path d="m6 9 6 6 6-6"/>',
  "bell-off": '<path d="M10.3 5.3A6 6 0 0 1 18 11v3l2 2H8"/><path d="M6.3 6.3A6 6 0 0 0 6 8v6l-2 2h11"/><path d="M10 20a2 2 0 0 0 4 0M3 3l18 18"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5 8.5 8.5 0 1 0 20.5 14.5Z"/>',
  monitor: '<rect x="2" y="3" width="20" height="15" rx="2"/><path d="M8 22h8m-4-4v4"/>',
};
export function icon(name,size=20){
  if (!Object.prototype.hasOwnProperty.call(paths,name)) return "";
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${paths[name]}</svg>`;
}
