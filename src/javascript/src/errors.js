/**
 * Custom exceptions used in JS modules
 */

export class NotImplementedError extends Error {
  constructor (message = 'Method not implemented') {
    super(message)
  }
}

export class RuntimeError extends Error {}
