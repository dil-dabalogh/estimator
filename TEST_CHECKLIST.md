# Testing Checklist

## Backend Tests

- [ ] Health endpoint responds: `curl http://localhost:8000/health`
- [ ] Batch endpoint accepts requests
- [ ] WebSocket connections established
- [ ] Parallel processing works for multiple URLs
- [ ] File downloads work for BA notes and PERT
- [ ] Error handling for invalid URLs
- [ ] Error handling for API failures

## Frontend Tests

- [ ] Form renders correctly
- [ ] Can add/remove URL rows
- [ ] Form validation works
- [ ] WebSocket connects and receives updates
- [ ] Results table displays correctly
- [ ] T-shirt size badges show correct colors
- [ ] Download buttons work
- [ ] Error messages display properly
- [ ] Responsive on mobile/tablet/desktop

## Integration Tests

- [ ] End-to-end flow with real Confluence URL
- [ ] End-to-end flow with real Jira URL
- [ ] Multiple simultaneous estimations
- [ ] Connection recovery after network interruption

## Deployment Tests

- [ ] Backend builds successfully
- [ ] Frontend builds successfully
- [ ] Lambda deployment via SAM
- [ ] Production environment variables configured
- [ ] S3 bucket hosting works
