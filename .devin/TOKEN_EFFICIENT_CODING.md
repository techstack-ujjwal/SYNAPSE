# Token-Efficient Coding Prompt

When writing code for this project, follow these principles to minimize token usage:

## Code Style Rules
1. **NO comments** in code unless absolutely critical (e.g., complex logic that cannot be self-documenting)
2. **Minimal console.log** - only for debugging, remove before committing
3. **Concise variable names** - use context-appropriate short names (e.g., `r` instead of `report` in simple loops)
4. **Inline arrow functions** for simple operations
5. **Destructure aggressively** - extract needed values in one line
6. **Avoid redundant parentheses** where operator precedence is clear
7. **Use template literals** instead of string concatenation
8. **Combine related operations** - don't split simple operations across lines
9. **Default to destructuring** - `const { id, name } = obj` instead of `const id = obj.id; const name = obj.name`
10. **Skip empty catch blocks** - use `.catch(() => {})` for no-op error handling

## Import Rules
- Import only what you use
- Use named imports instead of `import * as X`
- Group related imports on single lines when possible

## Function Rules
- Skip `return` keyword when body is single expression
- Use ternary operators for simple conditionals
- Use logical AND/OR for simple guards
- Combine related operations in single expressions

## Component Rules
- Skip unnecessary `useCallback`/`useMemo` unless performance is critical
- Use inline event handlers for simple functions
- Avoid wrapper divs when direct children work
- Use shorthand className concatenation

## API Call Rules
- Use `fetch().then().catch()` chain instead of async/await for simple calls
- Skip explicit `headers` when Content-Type is JSON (fetch defaults work)
- Combine fetch options into single object

## State Rules
- Use single state object instead of multiple related states
- Use functional updates when possible: `setCount(c => c + 1)` instead of `setCount(count + 1)`
- Skip loading states for instant operations

## Before Each Edit
Ask: "Can I make this shorter while keeping it readable?"
- If yes, refactor
- If no, proceed

## Example Transformation

BEFORE (verbose):
```typescript
// Fetch user data from API
const fetchUserData = async (userId: string) => {
  try {
    const response = await fetch(`${API_URL}/users/${userId}`);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching user:', error);
    return null;
  }
};
```

AFTER (token-efficient):
```typescript
const fetchUserData = (userId: string) => 
  fetch(`${API}/users/${userId}`).then(r => r.json()).catch(() => null);
```

## Goal
Write code that is:
- 30-50% shorter in tokens
- Still readable and maintainable
- Self-documenting through good naming
- Production-ready
