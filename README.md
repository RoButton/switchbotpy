# switchbot



# Switchbot BLE API


 <table>
  <tr>
    <th></th>
    <th colspan="3">Request</th>
    <th colspan="3">Notification</th>
    <th></th>
  </tr>
  <tr>
    <th>Name</th>
    <th>Handle</th>
    <th>Unencrypted</th>
    <th>Encrypted</th>
    <th>Required</th>
    <th>Handle</th>
    <th>Value</th>
    <th>Description</th>
  </tr>
  <tr>
    <td>press</td>
    <td>0x16</td>
    <td>0x 57 01</td>
    <td>0x 57 11 <pre>pw8</pre></td>
    <td></td>
    <td>0x13</td>
    <td>Value</td>
    <td>Desc</td>
  </tr>
  <tr>
    <td>press</td>
    <td>0x16</td>
    <td>0x 57 01</td>
    <td>0x 57 11 `pw8`</td>
    <td></td>
    <td>0x13</td>
    <td>Value</td>
    <td>Desc</td>
  </tr>
</table> 


|   Name                | Handle | Request Unencrypted       | Request Encrypted               | Notification Required | Handle | Value | Description |
| --------------------- |-----------:| -------------------------:| -------------------------------:|--------------|-----------:|--------------|-------------|
| press                 | 0x16       | 0x 57 01                  | 0x 57 11 `pw8`                  |              | 0x13       |              |             |
| turn on               | 0x16       | 0x 57 01 01               | 0x 57 11 `pw8` 01               |
| turn off              | 0x16       | 0x 57 01 02               | 0x 57 11 `pw8` 02               |
| set hold time         | 0x16       | 0x 57 0f 08 `sec2`        | 0x 57 1f `pw8` 08 `sec2`        |
| get timer             | 0x16       | 0x 57 08 `tid1`3          | 0x 57 18 `pw8` `tid1`3          |
| set timer             | 0x16       | 0x 57 09 `tid1`3 `tmr20`  | 0x 57 19 `pw8` `tid1`3 `tmr20`  |
| sync                  | 0x16       | 0x 57 09 01 `t16`         | 0x 57 19 `pw8` 01 `t16`         |
| set mode              | 0x16       | 0x 57 03 64 `ds1``inv1`   | 0x 57 13 `pw8` 64 `ds1``inv1`   |
| get settings          | 0x16       | 0x 57 02                  | 0x 57 12 `pw8`                  |
| get battery           | 0x16       |
| get firmware          | 0x16       |
| get dual state mode   | 0x16       |
| get inverse direction | 0x16       |
| get hold seconds      | 0x16       |

TODO [nku] maybe 3 in get timer is n_timer

| Variable | Description |
| -------- | ---------------------------------- |
| [pw8]     | 4 bytes crc32 checksum of password |
| [sec2]    | 1 byte unsigned integer of seconds |
| [tid1]    | timer id between 0 and 4 |
| [tmr20]    | [nt2] 00 [rep2] [hh2] [mm2] [md2] [act2] [its2] [ihh2] [imm2] |
| [t16]     | time in seconds utc + local offset from start |
| [ds1]     |
| []




