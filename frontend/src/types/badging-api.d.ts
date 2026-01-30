/**
 * Badging API type declarations
 *
 * Augments Navigator and WorkerNavigator with setAppBadge / clearAppBadge
 * so that strict-mode TypeScript compiles without errors.
 *
 * Spec: https://w3c.github.io/badging/
 */

interface Navigator {
  setAppBadge?(contents?: number): Promise<void>
  clearAppBadge?(): Promise<void>
}

interface WorkerNavigator {
  setAppBadge?(contents?: number): Promise<void>
  clearAppBadge?(): Promise<void>
}
