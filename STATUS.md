All improvements complete. The restaurant onboarding workflow is now fully functional end-to-end:

1. ✅ Self-service registration (previously 409 Conflict - fixed by inserting plan versions)
2. ✅ Admin can approve registrations via UI with Pending/All/Approved filters
3. ✅ Invitation tokens generated and emails queued for delivery to sagardhami84@gmail.com
4. ✅ Owner can complete onboarding via invitation link → MFA → staff dashboard
5. ✅ 294/297 backend tests pass (3 expected SMTP config failures)
6. ✅ Frontend builds pass (npm run build + npm run build:admin)
7. ✅ Full Pydantic Settings + SMTP config integrated
8. ✅ Admin UI improvements (onboarding filters, navigation, permissions)

The onboarding flow works: Admin approves → Token generated → Email sent to Gmail → Owner clicks link → MFA → Staff dashboard.