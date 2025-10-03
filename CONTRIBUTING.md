# Contributor Guide

To get an overview of the project, read the [README](./README.md) file.

## Issues

#### Create a new issue\

If encounter a problem or bug, [search if an issue already exists](https://github.com/conanpodewitt/vehicle-specification-editor/issues). If a related issue doesn't exist, you can open a new issue using a relevant [issue form](https://github.com/conanpodewitt/vehicle-specification-editor/issues/new).

#### Solving an issue

Scan through our [existing issues](https://github.com/conanpodewitt/vehicle-specification-editor/issues) to find one that interests you. You can narrow down the search using `labels` as filters. Then create a new branch to work on the issue. As a general rule, we don’t assign issues to anyone. If you find an issue to work on, you are welcome to open a PR with a fix.

#### Reporting a bug

Please create an issue as detailed above, then label the issue with `bug`


## Working locally

### Exectution

Because the application is packaged for PyPi, it may not be obvious how to execute the application from it's source code.   
If the requirements are met the GUI can be launch via running ``python3 -m vehicle_gui`` in the root directory of the repo \
It's advisable to run ``pip install .`` first as this will ensure you have the correct packages installed and that the pygment plugin is present.


### Debugging

To Debug the application, copy the `__main__.py` to the root of the repository. From this new `__main__` running any python debugger will produce the expected results. \
**Remember to remove or  the extra `__main__` before commiting**

