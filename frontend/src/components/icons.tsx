/** Icon set drawn for this product. Hairline geometric marks, no icon-library imports. */
import type { SVGProps } from 'react'

type P = SVGProps<SVGSVGElement> & { size?: number }

const base = (size: number) => ({
  width: size, height: size, viewBox: '0 0 24 24', fill: 'none',
  stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const, 'aria-hidden': true,
})

export const IconGauge = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M4 18a9 9 0 1 1 16 0" /><path d="M12 18l4-5" /><circle cx="12" cy="18" r="1.4" fill="currentColor" stroke="none" /></svg>
)
export const IconLadder = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M5 19V14M10 19V10M15 19V7M20 19V4" /></svg>
)
export const IconTarget = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3.4" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" /></svg>
)
export const IconBook = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H11v18H5.5A1.5 1.5 0 0 1 4 19.5z" /><path d="M20 4.5A1.5 1.5 0 0 0 18.5 3H13v18h5.5a1.5 1.5 0 0 0 1.5-1.5z" /></svg>
)
export const IconRoute = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><circle cx="5.5" cy="5.5" r="2.5" /><circle cx="18.5" cy="18.5" r="2.5" /><path d="M8 5.5h6a3 3 0 0 1 0 6H9a3 3 0 0 0 0 6h7" /></svg>
)
export const IconChat = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M20 14.5A2.5 2.5 0 0 1 17.5 17H8l-4 3.5V6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5z" /><path d="M8.5 8.5h7M8.5 12h4" /></svg>
)
export const IconDoc = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /><path d="M9 13h6M9 17h4" /></svg>
)
export const IconQuiz = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><rect x="3.5" y="4" width="17" height="16" rx="2" /><path d="M7.5 9.5h.01M7.5 14.5h.01M11 9.5h5.5M11 14.5h5.5" /></svg>
)
export const IconChart = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M4 20V4M4 20h16" /><rect x="7.5" y="12" width="3" height="5" /><rect x="13" y="8" width="3" height="9" /><rect x="18.5" y="14" width="2.5" height="3" /></svg>
)
export const IconShield = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M12 3l7 3v6c0 4.4-3 7.4-7 9-4-1.6-7-4.6-7-9V6z" /><path d="M9.2 12.2l2 2 3.6-3.8" /></svg>
)
export const IconUsers = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><circle cx="9" cy="8" r="3.2" /><path d="M3.5 20a5.5 5.5 0 0 1 11 0" /><path d="M16 5.2a3.2 3.2 0 0 1 0 5.9M17.5 14.4a5.5 5.5 0 0 1 3 5.1" /></svg>
)
export const IconGrid = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><rect x="3.5" y="3.5" width="7" height="7" rx="1" /><rect x="13.5" y="3.5" width="7" height="7" rx="1" /><rect x="3.5" y="13.5" width="7" height="7" rx="1" /><rect x="13.5" y="13.5" width="7" height="7" rx="1" /></svg>
)
export const IconPlug = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M9 3v5M15 3v5" /><path d="M6 8h12v3a6 6 0 0 1-6 6 6 6 0 0 1-6-6z" /><path d="M12 17v4" /></svg>
)
export const IconBell = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M6 9a6 6 0 1 1 12 0c0 4 1.5 5.5 1.5 5.5H4.5S6 13 6 9z" /><path d="M10 18a2 2 0 0 0 4 0" /></svg>
)
export const IconUser = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><circle cx="12" cy="8" r="3.4" /><path d="M5 20a7 7 0 0 1 14 0" /></svg>
)
export const IconCheck = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M5 12.5l4.5 4.5L19 6.5" /></svg>
)
export const IconX = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M6 6l12 12M18 6L6 18" /></svg>
)
export const IconPlus = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M12 5v14M5 12h14" /></svg>
)
export const IconArrow = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M5 12h13M13 6.5l5.5 5.5L13 17.5" /></svg>
)
export const IconChevron = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M9 5.5l6.5 6.5L9 18.5" /></svg>
)
export const IconRefresh = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M20 12a8 8 0 1 1-2.6-5.9" /><path d="M20 4v4.5h-4.5" /></svg>
)
export const IconUpload = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M12 17V4M7.5 8.5L12 4l4.5 4.5" /><path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" /></svg>
)
export const IconTrash = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M4 7h16M9.5 7V4.5h5V7M6.5 7l.8 13h9.4l.8-13" /><path d="M10.5 11v5M13.5 11v5" /></svg>
)
export const IconMenu = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M4 7h16M4 12h16M4 17h16" /></svg>
)
export const IconSearch = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><circle cx="10.5" cy="10.5" r="6" /><path d="M15 15l4.5 4.5" /></svg>
)
export const IconLock = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><rect x="4.5" y="10" width="15" height="10" rx="2" /><path d="M8 10V7.5a4 4 0 0 1 8 0V10" /></svg>
)
export const IconSpark = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M12 3l1.9 5.4L19.5 10l-5.6 1.6L12 17l-1.9-5.4L4.5 10l5.6-1.6z" /><path d="M18.5 16.5l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z" /></svg>
)
export const IconInfo = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><circle cx="12" cy="12" r="8.5" /><path d="M12 11v5.5M12 8h.01" /></svg>
)
export const IconAlert = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M12 4l8.5 15H3.5z" /><path d="M12 10v4M12 16.5h.01" /></svg>
)
export const IconDownload = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M12 4v13M7.5 12.5L12 17l4.5-4.5" /><path d="M4 19h16" /></svg>
)
export const IconLayers = ({ size = 16, ...p }: P) => (
  <svg {...base(size)} {...p}><path d="M12 3l8.5 4.5L12 12 3.5 7.5z" /><path d="M3.5 12.5L12 17l8.5-4.5" /><path d="M3.5 17L12 21.5 20.5 17" /></svg>
)
