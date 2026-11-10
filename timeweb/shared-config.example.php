<?php
/**
 * EXAMPLE ONLY. Place a private copy at:
 * <site-directory>/.bkm_private/config.php (one level above public_html).
 * Never upload this file or live values to public_html or GitHub.
 */
return [
  'enabled' => false,             // set true only after HTTPS and testing
  'privacy_approved' => true,     // company-approved policy already linked
  'assigned_by_id' => 7,
  'rate_salt' => 'GENERATE_RANDOM_64_CHARACTER_STRING_HERE_NOT_THIS_EXAMPLE',
  'bitrix_webhook_url' => 'https://bitrix.24bkm.com/rest/ID/SECRET/'
];
