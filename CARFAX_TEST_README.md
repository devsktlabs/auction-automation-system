# CARFAX Integration Test Script

## Overview
The `test_carfax_manual.py` script allows you to test the CARFAX dealer portal integration with specific VIN numbers. It provides a user-friendly interface to verify that your CARFAX credentials work and that the web scraping integration can successfully extract vehicle history data.

## Quick Start

### 1. Set Up Credentials (Recommended)
```bash
export CARFAX_DEALER_USERNAME="your_username"
export CARFAX_DEALER_PASSWORD="your_password"
```

### 2. Run Interactive Test
```bash
python test_carfax_manual.py
```
This will prompt you to enter VIN numbers one by one.

### 3. Test Specific VINs
```bash
python test_carfax_manual.py --vins 1HGBH41JXMN109186 2HGBH41JXMN109187
```

## Usage Examples

### Interactive Mode (Recommended for First Test)
```bash
python test_carfax_manual.py
```
- Prompts for credentials if not in environment
- Allows you to enter VINs one by one
- Shows real-time progress and results

### Command Line Mode
```bash
# Test multiple VINs at once
python test_carfax_manual.py --vins 1HGBH41JXMN109186 2HGBH41JXMN109187 3HGBH41JXMN109188

# Force credential prompt (useful for testing different accounts)
python test_carfax_manual.py --prompt-credentials

# Custom timeout (useful for slow connections)
python test_carfax_manual.py --timeout 60

# Save results to specific file
python test_carfax_manual.py --output my_test_results.json
```

## What the Script Does

1. **Credential Management**: Securely prompts for CARFAX dealer portal credentials if not found in environment variables
2. **VIN Validation**: Validates VIN format before attempting lookup
3. **Web Scraping**: Uses the CARFAX integration to scrape vehicle history from the dealer portal
4. **Data Analysis**: Analyzes the extracted data for red flags, yellow flags, and green flags
5. **Performance Monitoring**: Times each request to help understand performance
6. **Error Handling**: Captures and displays any errors encountered during the process
7. **Results Export**: Saves detailed results to a timestamped JSON file

## Output Format

### Console Output
The script provides real-time feedback with:
- ✅ Success indicators
- ❌ Error messages
- 🔍 Progress updates
- 📋 Vehicle history summaries
- 🟢🟡🔴 Risk level indicators
- ⏱️ Timing information

### JSON Results File
Results are saved to `carfax_test_results_YYYYMMDD_HHMMSS.json` containing:
```json
{
  "test_metadata": {
    "timestamp": "2025-07-13T...",
    "total_vins_tested": 2,
    "successful_tests": 2,
    "failed_tests": 0
  },
  "results": [
    {
      "vin": "1HGBH41JXMN109186",
      "success": true,
      "elapsed_seconds": 12.34,
      "data": { ... },
      "flags_analysis": { ... }
    }
  ]
}
```

## Sample VINs for Testing

Here are some sample VIN formats you can use for testing (these are example formats, not real vehicles):
- `1HGBH41JXMN109186` (Honda format)
- `2HGBH41JXMN109187` (Honda format)
- `3VWDX7AJ5DM000001` (Volkswagen format)
- `1FTFW1ET5DFC12345` (Ford format)

**Note**: Use real VINs from your inventory for actual testing.

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```
   Error importing CARFAX integration
   ```
   - Make sure you're running from the `auction_automation_system` directory
   - Check that all dependencies are installed

2. **Authentication Failures**
   ```
   CARFAX login failed: Invalid credentials
   ```
   - Verify your dealer portal username and password
   - Try logging in manually to the CARFAX dealer portal first
   - Use `--prompt-credentials` to re-enter credentials

3. **Timeout Errors**
   ```
   TimeoutException: Element not found
   ```
   - Increase timeout with `--timeout 60`
   - Check your internet connection
   - CARFAX portal might be slow or under maintenance

4. **Rate Limiting**
   ```
   Rate limit exceeded
   ```
   - The script includes built-in delays between requests
   - Wait a few minutes before retrying
   - Test fewer VINs at once

### Debug Mode
For detailed debugging information, check the logs in the auction system's log directory.

## Security Notes

- Credentials are prompted securely using `getpass` (password won't be visible)
- Environment variables are the recommended way to store credentials
- The script doesn't log or save credentials to files
- Session data is cached locally to avoid repeated logins

## Performance Expectations

- **First VIN**: 15-30 seconds (includes login time)
- **Subsequent VINs**: 8-15 seconds each
- **Rate Limiting**: 3-second delay between requests
- **Session Reuse**: Faster subsequent runs within 24 hours

## Next Steps

After successful testing:
1. Review the JSON results file for data quality
2. Check that all expected vehicle information is being extracted
3. Verify that the risk analysis flags are working correctly
4. Integrate the CARFAX data into your auction automation workflows

## Support

If you encounter issues:
1. Check the console output for specific error messages
2. Review the generated JSON file for partial data
3. Try testing with a single VIN first
4. Verify your CARFAX dealer portal access manually
