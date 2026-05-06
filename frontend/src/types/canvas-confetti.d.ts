declare module 'canvas-confetti' {
  interface Options {
    particleCount?: number
    spread?: number
    origin?: { x?: number; y?: number }
    colors?: string[]
    shapes?: string[]
    scalar?: number
    gravity?: number
    drift?: number
    ticks?: number
    startVelocity?: number
    decay?: number
    zIndex?: number
  }
  function confetti(options?: Options): Promise<null>
  export = confetti
}
