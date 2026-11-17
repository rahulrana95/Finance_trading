import { DEFAULT_ERROR } from '../constants'

/** The message to show for anything that was thrown. */
export const messageOf = (error: unknown, fallback: string = DEFAULT_ERROR): string =>
  error instanceof Error ? error.message : fallback
