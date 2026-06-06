# TODO - SHIVA AI Jarvis (Frontend)

## Sprint 1–2 (Critical)
- [x] Fix SSE stream parsing + add AbortSignal support in `apps/web/src/api.ts`
- [x] Fix SSE race condition by aborting in-flight streams + retry cancellation in `apps/web/src/components/Chat.tsx`
- [x] Improve crash recovery UX in `apps/web/src/components/ErrorBoundary.tsx`
- [ ] Remove duplicate chat state management between `apps/web/src/App.tsx` and `apps/web/src/components/Chat.tsx`

## Security
- [ ] Audit all frontend HTML sinks (e.g., `dangerouslySetInnerHTML`).
- [ ] If any HTML rendering exists, add DOMPurify + `src/utils/sanitize.ts`.

## Performance / Architecture (High)
- [ ] Refactor monolithic `apps/web/src/App.tsx` into feature workspaces/hooks.
- [ ] Introduce React Query caching via `@tanstack/react-query`.
- [ ] Add skeleton/loading states for all workspace lists.

## Medium
- [ ] Validate required env vars (optional `.env.example`).
- [ ] Remove unused dependencies after audit.
- [ ] Add accessibility improvements (keyboard shortcuts, aria correctness).

## Notes
- Vite build for `apps/web` completed successfully after streaming fixes.

