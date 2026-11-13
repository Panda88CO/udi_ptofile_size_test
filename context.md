## 2026-11-13T19:08:21.825750+00:00

Initial scaffold: port of Panda88CO/udi-yolink profile-size-test (profile_size_test.py) into a Controller plugin with a separate class-free engine module (make_engine factory), custom params, two commands, and unit tests.

Sources consulted: 0.1.4 dynamic profile fails on PG3x 3.4.25/IoX 6.1.2 · Issue #2 · Panda88CO/udi-Kidde · GitHub, Panda88CO - Overview, Panda88's Content - Universal Devices Forum, GitHub - Panda88CO/udi-yolink: ISY integration of YoLink devices · GitHub (MIT), Dev2 by Panda88CO · Pull Request #1 · Panda88CO/udi-nuheatv2 · GitHub (MIT), GitHub - Panda88CO/udi-MonitorAlert · GitHub (MIT), Answers from Panda88 - Universal Devices Forum, GitHub - sejgit/udi-yolink · GitHub (MIT), ILauncherProfileManager::LoadJSONProfile, https://github.com/Panda88CO/udi-yolink/tree/profile-size-test/profile_size_test, https://api.github.com/repos/Panda88CO/udi-yolink/contents/profile_size_test?ref=profile-size-test, https://raw.githubusercontent.com/Panda88CO/udi-yolink/profile-size-test/profile_size_test/README.md, https://raw.githubusercontent.com/Panda88CO/udi-yolink/profile-size-test/profile_size_test/profile_size_test.py

## 2026-11-13T19:18:55.500041+00:00

Records the v1.0.1 changes, whose own context entry was skipped by a permission error on install.sh: result readouts moved to a ResultsNode child (the Controller template only declares ST, so setDriver on other ids was a silent error); stray CDATA wrapper removed from the parameter docs; sweep test expectation corrected to 5 sizes against a 64 KB limit. Installed in slot 4. v1.0.2 is a version bump only.

