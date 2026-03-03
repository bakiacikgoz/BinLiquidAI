import { isOperatorIdValid } from './settings';

export function canMutateWithOperatorId(operatorId: string, contractMismatch: boolean): boolean {
  return isOperatorIdValid(operatorId) && !contractMismatch;
}

export function actorForOperator(operatorId: string): string {
  return `ui:${operatorId.trim()}`;
}
