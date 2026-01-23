# Debugging Daily Reminder Issues

This document explains how to debug and troubleshoot the daily 20:00 reminder functionality.

## Overview

The daily reminder system consists of:
1. **Daily Check Job**: Scheduled to run at 20:00 every day
2. **Student Question**: Sends "Hast du heute auch gelernt?" to the student
3. **Parent Notification**: Informs parent that question was sent
4. **Response Handling**: Processes student's yes/no answer
5. **Parent Feedback**: Sends student's response to parent

## Common Issues & Solutions

### 1. Daily Reminder Not Sent

**Symptoms**: No 20:00 reminder is sent to the student.

**Check**: Look for these log messages:
```
daily_check: Starting 20:00 daily check
daily_check: STUDENT_CHAT_ID not set - skipping daily check
```

**Solution**: Ensure `STUDENT_CHAT_ID` is properly set in your `.env` file:
```bash
STUDENT_CHAT_ID=123456789  # Replace with actual student chat ID
```

### 2. Parent Not Receiving Notifications

**Symptoms**: Student gets the question but parent doesn't get notifications.

**Check**: Look for these log messages:
```
daily_check: No parent notification (PARENT_CHAT_ID not set or same as student)
```

**Solution**: Ensure `PARENT_CHAT_ID` is properly set and different from `STUDENT_CHAT_ID`:
```bash
PARENT_CHAT_ID=987654321   # Replace with actual parent chat ID
STUDENT_CHAT_ID=123456789  # Must be different from parent
```

### 3. Response Callbacks Not Working

**Symptoms**: Student can't click yes/no buttons, or parent doesn't get response.

**Check**: Look for these log messages:
```
on_learned_response: Received callback 'learned_yes' from chat 123456789
on_learned_response: Sent 'YES' notification to parent 987654321
```

**Solution**: Verify callback handlers are registered and environment variables are correct.

## Manual Testing

### Test Daily Check Function

Use the new `/testdaily` command to manually trigger the daily check:

1. Send `/testdaily` to the bot
2. Check logs for detailed execution information
3. Verify student receives the question
4. Verify parent receives notification

### Test Response Handling

1. Trigger daily check with `/testdaily`
2. Click "Ja ✅" or "Nein ❌" buttons
3. Check logs for callback processing
4. Verify parent receives student's response

## Log Messages Reference

### Daily Check Logs

| Message | Meaning |
|---------|---------|
| `daily_check: Starting 20:00 daily check` | Function started successfully |
| `daily_check: STUDENT_CHAT_ID not set - skipping daily check` | Missing configuration |
| `daily_check: Successfully sent question to student X` | Question sent to student |
| `daily_check: Successfully sent info to parent X` | Parent notification sent |
| `daily_check: Error during daily check: ...` | Error occurred |

### Response Handler Logs

| Message | Meaning |
|---------|---------|
| `on_learned_response: Received callback 'learned_yes'` | Student clicked yes |
| `on_learned_response: Received callback 'learned_no'` | Student clicked no |
| `on_learned_response: Sent 'YES' notification to parent` | Parent notified of yes |
| `on_learned_response: Sent 'NO' notification to parent` | Parent notified of no |

### Scheduling Logs

| Message | Meaning |
|---------|---------|
| `schedule_all_reminders: Scheduled daily_check at 20:00` | Daily job scheduled |
| `schedule_all_reminders: STUDENT_CHAT_ID = X` | Shows current configuration |
| `schedule_all_reminders: PARENT_CHAT_ID = X` | Shows current configuration |

## Configuration Checklist

- [ ] `TELEGRAM_TOKEN` is set and valid
- [ ] `STUDENT_CHAT_ID` is set to student's chat ID (not 0)
- [ ] `PARENT_CHAT_ID` is set to parent's chat ID (not 0)
- [ ] `STUDENT_CHAT_ID` ≠ `PARENT_CHAT_ID` (must be different)
- [ ] Both users have started the bot with `/start`
- [ ] Bot has permissions to send messages to both chats

## Advanced Debugging

1. **Check Job Queue**: The daily check is scheduled as a job named `daily_check_20`
2. **Timezone**: Jobs run in `Europe/Berlin` timezone
3. **Error Handling**: All errors are logged with full stack traces
4. **Manual Testing**: Use `/testdaily` command for immediate testing

## Getting Help

If issues persist:
1. Check bot logs for detailed error messages
2. Verify all environment variables are set correctly
3. Test with `/testdaily` command
4. Ensure both student and parent have interacted with the bot via `/start`