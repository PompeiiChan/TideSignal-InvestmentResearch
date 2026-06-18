import { useId } from 'react'
import './TideSignalAnimatedLogo.css'

export function TideSignalAnimatedLogo() {
  const gradientId = `tideGradient-${useId().replace(/:/g, '')}`

  return (
    <div className="tidesignal-logo-wrap" aria-label="TideSignal animated logo">
      <div className="ambient-ring" />
      <div className="glow" />
      <svg viewBox="0 0 512 512" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="潮声 TideSignal 海浪动效 Logo">
        <defs>
          <linearGradient id={gradientId} x1="118" y1="116" x2="394" y2="396" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor="#0B2E5E" />
            <stop offset="0.50" stopColor="#2563EB" />
            <stop offset="1" stopColor="#60A5FA" />
          </linearGradient>
        </defs>

        <g className="wave-main">
          <path
            d="M121 321C147 222 234 155 338 157C363 158 386 164 407 175L360 222C337 211 311 208 285 215C237 227 200 268 191 321H121Z"
            fill={`url(#${gradientId})`}
          />
          <path
            d="M122 348H278C319 348 358 332 386 304L410 281C393 331 345 367 288 371C222 376 161 361 122 348Z"
            fill={`url(#${gradientId})`}
          />
          <path
            d="M191 321C200 268 237 227 285 215C311 208 337 211 360 222L309 273C287 263 263 269 247 285C239 294 234 306 232 321H191Z"
            fill="#DBEAFE"
            fillOpacity="0.96"
          />
          <path
            className="crest-highlight"
            d="M145 320C171 242 243 190 326 190"
            stroke="white"
            strokeOpacity="0.72"
            strokeWidth="14"
            strokeLinecap="round"
          />
          <circle className="spark" cx="367" cy="182" r="8" fill="#60A5FA" fillOpacity="0.86" />
        </g>

        <path
          className="echo-line-1"
          d="M155 381C201 399 304 406 365 357"
          stroke="#60A5FA"
          strokeOpacity="0.36"
          strokeWidth="13"
          strokeLinecap="round"
        />
        <path
          className="echo-line-2"
          d="M170 403C218 417 289 420 337 391"
          stroke="#60A5FA"
          strokeOpacity="0.20"
          strokeWidth="10"
          strokeLinecap="round"
        />
      </svg>
    </div>
  )
}
