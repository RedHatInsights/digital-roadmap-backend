MODULE_DATA = {
    8: [
        {
            "module_name": "go-toolset",
            "streams": [
                {
                    "name": "go-toolset",
                    "stream": "rhel8",
                    "context": "b754926a",
                    "arch": "x86_64",
                    "version": "820190208025401",
                    "description": "Go Tools and libraries",
                    "profiles": {"common": ["go-toolset"]},
                }
            ],
        },
        {
            "module_name": "satellite-5-client",
            "streams": [
                {
                    "name": "satellite-5-client",
                    "stream": "1",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820190204085912",
                    "description": "Red Hat Satellite 5 client packages provide programs and libraries to allow your system to receive software updates from Red Hat Satellite 5.",
                    "profiles": {
                        "common": ["dnf-plugin-spacewalk", "rhn-client-tools", "rhn-setup", "rhnlib", "rhnsd"],
                        "gui": [
                            "dnf-plugin-spacewalk",
                            "rhn-client-tools",
                            "rhn-setup",
                            "rhn-setup-gnome",
                            "rhnlib",
                            "rhnsd",
                        ],
                    },
                }
            ],
        },
        {
            "module_name": "swig",
            "streams": [
                {
                    "name": "swig",
                    "stream": "3",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820181213143944",
                    "description": "Simplified Wrapper and Interface Generator (SWIG) is a software development tool for connecting C, C++ and Objective C programs with a variety of high-level programming languages. SWIG is primarily used with Perl, Python and Tcl/TK, but it has also been extended to Java, Eiffel and Guile. SWIG is normally used to create high-level interpreted programming environments, systems integration, and as a tool for building user interfaces\n",
                    "profiles": {"common": ["swig"], "complete": ["swig", "swig-doc", "swig-gdb"]},
                },
                {
                    "name": "swig",
                    "stream": "4",
                    "context": "9f9e2e7e",
                    "arch": "x86_64",
                    "version": "8040020201001104431",
                    "description": "Simplified Wrapper and Interface Generator (SWIG) is a software development tool for connecting C, C++ and Objective C programs with a variety of high-level programming languages. SWIG is primarily used with Perl, Python and Tcl/TK, but it has also been extended to Java, Eiffel and Guile. SWIG is normally used to create high-level interpreted programming environments, systems integration, and as a tool for building user interfaces\n",
                    "profiles": {"common": ["swig"], "complete": ["swig", "swig-doc", "swig-gdb"]},
                },
                {
                    "name": "swig",
                    "stream": "4.1",
                    "context": "fd72936b",
                    "arch": "x86_64",
                    "version": "8080020221213075530",
                    "description": "Simplified Wrapper and Interface Generator (SWIG) is a software development tool for connecting C, C++ and Objective C programs with a variety of high-level programming languages. SWIG is primarily used with Perl, Python and Tcl/TK, but it has also been extended to Java, Eiffel and Guile. SWIG is normally used to create high-level interpreted programming environments, systems integration, and as a tool for building user interfaces\n",
                    "profiles": {"common": ["swig"], "complete": ["swig", "swig-doc", "swig-gdb"]},
                },
            ],
        },
        {
            "module_name": "pmdk",
            "streams": [
                {
                    "name": "pmdk",
                    "stream": "1_fileformat_v6",
                    "context": "fd72936b",
                    "arch": "x86_64",
                    "version": "8080020221121213140",
                    "description": "The Persistent Memory Development Kit is a collection of libraries for using memory-mapped persistence, optimized specifically for persistent memory.",
                    "profiles": {},
                }
            ],
        },
        {
            "module_name": "subversion",
            "streams": [
                {
                    "name": "subversion",
                    "stream": "1.1",
                    "context": "a51370e3",
                    "arch": "x86_64",
                    "version": "820181215112250",
                    "description": "Apache Subversion, a Modern Version Control System",
                    "profiles": {
                        "common": ["subversion", "subversion-libs", "subversion-tools"],
                        "server": ["mod_dav_svn", "subversion", "subversion-libs", "subversion-tools"],
                    },
                },
                {
                    "name": "subversion",
                    "stream": "1.10",
                    "context": "78111232",
                    "arch": "x86_64",
                    "version": "8070020220701055908",
                    "description": "Apache Subversion, a Modern Version Control System",
                    "profiles": {
                        "common": ["subversion", "subversion-libs", "subversion-tools"],
                        "server": ["mod_dav_svn", "subversion", "subversion-libs", "subversion-tools"],
                    },
                },
                {
                    "name": "subversion",
                    "stream": "1.14",
                    "context": "a74460ab",
                    "arch": "x86_64",
                    "version": "8070020220701055624",
                    "description": "Apache Subversion, a Modern Version Control System",
                    "profiles": {
                        "common": ["subversion", "subversion-libs", "subversion-tools"],
                        "server": ["mod_dav_svn", "subversion", "subversion-libs", "subversion-tools"],
                    },
                },
            ],
        },
        {
            "module_name": "rust-toolset",
            "streams": [
                {
                    "name": "rust-toolset",
                    "stream": "rhel8",
                    "context": "b09eea91",
                    "arch": "x86_64",
                    "version": "820181214214108",
                    "description": "Rust Toolset",
                    "profiles": {"common": ["rust-toolset"]},
                }
            ],
        },
        {
            "module_name": "jaxb",
            "streams": [
                {
                    "name": "jaxb",
                    "stream": "4",
                    "context": "9d367344",
                    "arch": "x86_64",
                    "version": "8080020230207081414",
                    "description": "Jakarta XML Binding defines an API and tools that automate the mapping between XML documents and Java objects. The Eclipse Implementation of JAXB project contains implementation of Jakarta XML Binding API.",
                    "profiles": {"common": ["jaxb-runtime"]},
                }
            ],
        },
        {
            "module_name": "python39",
            "streams": [
                {
                    "name": "python39",
                    "stream": "3.9",
                    "context": "d47b87a4",
                    "arch": "x86_64",
                    "version": "8100020240927003152",
                    "description": "This module gives users access to the internal Python 3.9 in RHEL8, as\nwell as provides some additional Python packages the users might need.\nIn addition to these you can install any python3-* package available\nin RHEL and use it with Python from this module.",
                    "profiles": {
                        "build": ["python39", "python39-devel", "python39-rpm-macros"],
                        "common": ["python39"],
                    },
                }
            ],
        },
        {
            "module_name": "perl-DBD-SQLite",
            "streams": [
                {
                    "name": "perl-DBD-SQLite",
                    "stream": "1.58",
                    "context": "6bc6cad6",
                    "arch": "x86_64",
                    "version": "820181214121133",
                    "description": "SQLite is a public domain RDBMS database engine that you can find at http://www.hwaci.com/sw/sqlite/. This Perl module provides a SQLite RDBMS module that uses the system SQLite libraries.\n",
                    "profiles": {"common": ["perl-DBD-SQLite"]},
                }
            ],
        },
        {
            "module_name": "python27",
            "streams": [
                {
                    "name": "python27",
                    "stream": "2.7",
                    "context": "43711c95",
                    "arch": "x86_64",
                    "version": "820190212161047",
                    "description": "This module provides the Python 2.7 interpreter and additional Python\npackages the users might need.",
                    "profiles": {"common": ["python2", "python2-libs", "python2-pip", "python2-setuptools"]},
                }
            ],
        },
        {
            "module_name": "postgresql",
            "streams": [
                {
                    "name": "postgresql",
                    "stream": "10",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820190104140132",
                    "description": "PostgreSQL is an advanced Object-Relational database management system (DBMS). The postgresql-server package contains the programs needed to create and run a PostgreSQL server, which will in turn allow you to create and maintain PostgreSQL databases. The base postgresql package contains the client programs that you'll need to access a PostgreSQL DBMS server.",
                    "profiles": {"client": ["postgresql"], "server": ["postgresql-server"]},
                },
                {
                    "name": "postgresql",
                    "stream": "12",
                    "context": "489197000000",
                    "arch": "x86_64",
                    "version": "8100020241122084405",
                    "description": "PostgreSQL is an advanced Object-Relational database management system (DBMS). The postgresql-server package contains the programs needed to create and run a PostgreSQL server, which will in turn allow you to create and maintain PostgreSQL databases. The base postgresql package contains the client programs that you'll need to access a PostgreSQL DBMS server.",
                    "profiles": {"client": ["postgresql"], "server": ["postgresql-server"]},
                },
                {
                    "name": "postgresql",
                    "stream": "13",
                    "context": "489197000000",
                    "arch": "x86_64",
                    "version": "8100020241122084628",
                    "description": "PostgreSQL is an advanced Object-Relational database management system (DBMS). The postgresql-server package contains the programs needed to create and run a PostgreSQL server, which will in turn allow you to create and maintain PostgreSQL databases. The base postgresql package contains the client programs that you'll need to access a PostgreSQL DBMS server.",
                    "profiles": {"client": ["postgresql"], "server": ["postgresql-server"]},
                },
                {
                    "name": "postgresql",
                    "stream": "15",
                    "context": "489197000000",
                    "arch": "x86_64",
                    "version": "8100020241122084744",
                    "description": "PostgreSQL is an advanced Object-Relational database management system (DBMS). The postgresql-server package contains the programs needed to create and run a PostgreSQL server, which will in turn allow you to create and maintain PostgreSQL databases. The base postgresql package contains the client programs that you'll need to access a PostgreSQL DBMS server.",
                    "profiles": {"client": ["postgresql"], "server": ["postgresql-server"]},
                },
                {
                    "name": "postgresql",
                    "stream": "16",
                    "context": "489197000000",
                    "arch": "x86_64",
                    "version": "8100020241122085009",
                    "description": "PostgreSQL is an advanced Object-Relational database management system (DBMS). The postgresql-server package contains the programs needed to create and run a PostgreSQL server, which will in turn allow you to create and maintain PostgreSQL databases. The base postgresql package contains the client programs that you'll need to access a PostgreSQL DBMS server.",
                    "profiles": {"client": ["postgresql"], "server": ["postgresql-server"]},
                },
                {
                    "name": "postgresql",
                    "stream": "9.6",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820190104140337",
                    "description": "PostgreSQL is an advanced Object-Relational database management system (DBMS). The postgresql-server package contains the programs needed to create and run a PostgreSQL server, which will in turn allow you to create and maintain PostgreSQL databases. The base postgresql package contains the client programs that you'll need to access a PostgreSQL DBMS server.",
                    "profiles": {"client": ["postgresql"], "server": ["postgresql-server"]},
                },
            ],
        },
        {
            "module_name": "varnish",
            "streams": [
                {
                    "name": "varnish",
                    "stream": "6",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820181213144015",
                    "description": "Varnish Cache web application accelerator",
                    "profiles": {"common": ["varnish", "varnish-modules"]},
                }
            ],
        },
        {
            "module_name": "mysql",
            "streams": [
                {
                    "name": "mysql",
                    "stream": "8",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820190104140943",
                    "description": "MySQL is a multi-user, multi-threaded SQL database server. MySQL is a client/server implementation consisting of a server daemon (mysqld) and many different client programs and libraries. The base package contains the standard MySQL client programs and generic MySQL files.",
                    "profiles": {"client": ["mysql"], "server": ["mysql-server"]},
                },
                {
                    "name": "mysql",
                    "stream": "8.0",
                    "context": "a75119d5",
                    "arch": "x86_64",
                    "version": "8090020240126173013",
                    "description": "MySQL is a multi-user, multi-threaded SQL database server. MySQL is a client/server implementation consisting of a server daemon (mysqld) and many different client programs and libraries. The base package contains the standard MySQL client programs and generic MySQL files.",
                    "profiles": {"client": ["mysql"], "server": ["mysql-server"]},
                },
            ],
        },
        {
            "module_name": "nginx",
            "streams": [
                {
                    "name": "nginx",
                    "stream": "1.14",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820181214004940",
                    "description": "nginx 1.14 webserver module",
                    "profiles": {
                        "common": [
                            "nginx",
                            "nginx-all-modules",
                            "nginx-filesystem",
                            "nginx-mod-http-image-filter",
                            "nginx-mod-http-perl",
                            "nginx-mod-http-xslt-filter",
                            "nginx-mod-mail",
                            "nginx-mod-stream",
                        ]
                    },
                },
                {
                    "name": "nginx",
                    "stream": "1.16",
                    "context": "522a0ee4",
                    "arch": "x86_64",
                    "version": "8040020210526102347",
                    "description": "nginx 1.16 webserver module",
                    "profiles": {
                        "common": [
                            "nginx",
                            "nginx-all-modules",
                            "nginx-filesystem",
                            "nginx-mod-http-image-filter",
                            "nginx-mod-http-perl",
                            "nginx-mod-http-xslt-filter",
                            "nginx-mod-mail",
                            "nginx-mod-stream",
                        ]
                    },
                },
                {
                    "name": "nginx",
                    "stream": "1.18",
                    "context": "522a0ee4",
                    "arch": "x86_64",
                    "version": "8040020210526100943",
                    "description": "nginx 1.18 webserver module",
                    "profiles": {
                        "common": [
                            "nginx",
                            "nginx-all-modules",
                            "nginx-filesystem",
                            "nginx-mod-http-image-filter",
                            "nginx-mod-http-perl",
                            "nginx-mod-http-xslt-filter",
                            "nginx-mod-mail",
                            "nginx-mod-stream",
                        ]
                    },
                },
                {
                    "name": "nginx",
                    "stream": "1.20",
                    "context": "63b34585",
                    "arch": "x86_64",
                    "version": "8080020231012034601",
                    "description": "nginx 1.20 webserver module",
                    "profiles": {
                        "common": [
                            "nginx",
                            "nginx-all-modules",
                            "nginx-filesystem",
                            "nginx-mod-http-image-filter",
                            "nginx-mod-http-perl",
                            "nginx-mod-http-xslt-filter",
                            "nginx-mod-mail",
                            "nginx-mod-stream",
                        ]
                    },
                },
                {
                    "name": "nginx",
                    "stream": "1.22",
                    "context": "63b34585",
                    "arch": "x86_64",
                    "version": "8080020231011224613",
                    "description": "nginx 1.22 webserver module",
                    "profiles": {
                        "common": [
                            "nginx",
                            "nginx-all-modules",
                            "nginx-filesystem",
                            "nginx-mod-http-image-filter",
                            "nginx-mod-http-perl",
                            "nginx-mod-http-xslt-filter",
                            "nginx-mod-mail",
                            "nginx-mod-stream",
                        ]
                    },
                },
                {
                    "name": "nginx",
                    "stream": "1.24",
                    "context": "e155f54d",
                    "arch": "x86_64",
                    "version": "8100020240119085512",
                    "description": "nginx 1.24 webserver module",
                    "profiles": {
                        "common": [
                            "nginx",
                            "nginx-all-modules",
                            "nginx-filesystem",
                            "nginx-mod-http-image-filter",
                            "nginx-mod-http-perl",
                            "nginx-mod-http-xslt-filter",
                            "nginx-mod-mail",
                            "nginx-mod-stream",
                        ]
                    },
                },
            ],
        },
        {
            "module_name": "rhn-tools",
            "streams": [
                {
                    "name": "rhn-tools",
                    "stream": "1",
                    "context": "e122ddfa",
                    "arch": "x86_64",
                    "version": "820190321094720",
                    "description": "Red Hat Satellite 5 tools packages providing additional functionality like e.g. provisioning or configuration management.",
                    "profiles": {
                        "common": [
                            "koan",
                            "osad",
                            "python3-spacewalk-backend-libs",
                            "rhn-custom-info",
                            "rhn-virtualization-host",
                            "rhncfg",
                            "rhncfg-actions",
                            "rhncfg-client",
                            "rhncfg-management",
                            "rhnpush",
                            "spacewalk-abrt",
                            "spacewalk-client-cert",
                            "spacewalk-koan",
                            "spacewalk-oscap",
                            "spacewalk-remote-utils",
                            "spacewalk-usix",
                        ]
                    },
                }
            ],
        },
        {
            "module_name": "perl-DBI",
            "streams": [
                {
                    "name": "perl-DBI",
                    "stream": "1.641",
                    "context": "2fbcbb20",
                    "arch": "x86_64",
                    "version": "820190116185335",
                    "description": "DBI is a database access Application Programming Interface (API) for the Perl language. The DBI API specification defines a set of functions, variables and conventions that provide a consistent database interface independent of the actual database being used.\n",
                    "profiles": {"common": ["perl-DBI"]},
                }
            ],
        },
        {
            "module_name": "pki-core",
            "streams": [
                {
                    "name": "pki-core",
                    "stream": "10.6",
                    "context": "5a87be8a",
                    "arch": "x86_64",
                    "version": "820190128182152",
                    "description": "A module for PKI Core packages.",
                    "profiles": {},
                }
            ],
        },
        {
            "module_name": "llvm-toolset",
            "streams": [
                {
                    "name": "llvm-toolset",
                    "stream": "rhel8",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820190207221833",
                    "description": "LLVM Tools and libraries",
                    "profiles": {"common": ["llvm-toolset"]},
                }
            ],
        },
        {
            "module_name": "log4j",
            "streams": [
                {
                    "name": "log4j",
                    "stream": "2",
                    "context": "9d367344",
                    "arch": "x86_64",
                    "version": "8080020221020123337",
                    "description": "Log4j is a popular Java logging library that allows the programmer to output log statements to a variety of output targets.",
                    "profiles": {"common": ["log4j"]},
                }
            ],
        },
        {
            "module_name": "perl-FCGI",
            "streams": [
                {
                    "name": "perl-FCGI",
                    "stream": "0.78",
                    "context": "2fbcbb20",
                    "arch": "x86_64",
                    "version": "820181214153815",
                    "description": "This allows you to write a FastCGI client in the Perl language.\n",
                    "profiles": {"common": ["perl-FCGI"]},
                }
            ],
        },
        {
            "module_name": "perl-IO-Socket-SSL",
            "streams": [
                {
                    "name": "perl-IO-Socket-SSL",
                    "stream": "2.066",
                    "context": "03d935ed",
                    "arch": "x86_64",
                    "version": "8060020211122104554",
                    "description": "IO::Socket::SSL is a drop-in replacement for IO::Socket::IP that uses TLS to encrypt data before it is transferred to a remote server or client. IO::Socket::SSL supports all the extra features that one needs to write a full-featured TLS client or server application like multiple TLS contexts, cipher selection, certificate verification, and TLS version selection. Net::SSLeay offers some high level convenience functions for accessing web pages on TLS servers, a sslcat() function for writing your own clients, and finally access to the API of OpenSSL library so you can write servers or clients for more complicated applications.\n",
                    "profiles": {"common": ["perl-IO-Socket-SSL", "perl-Net-SSLeay"]},
                }
            ],
        },
        {
            "module_name": "python38",
            "streams": [
                {
                    "name": "python38",
                    "stream": "3.8",
                    "context": "d9f72c26",
                    "arch": "x86_64",
                    "version": "8090020230810143931",
                    "description": "This module gives users access to the internal Python 3.8 in RHEL8, as\nwell as provides some additional Python packages the users might need.\nIn addition to these you can install any python3-* package available\nin RHEL and use it with Python from this module.",
                    "profiles": {
                        "build": ["python38", "python38-devel", "python38-rpm-macros"],
                        "common": ["python38"],
                    },
                }
            ],
        },
        {
            "module_name": "eclipse",
            "streams": [
                {
                    "name": "eclipse",
                    "stream": "rhel8",
                    "context": "498c0fee",
                    "arch": "x86_64",
                    "version": "8030020201023061315",
                    "description": "The Eclipse platform is designed for building integrated development environments (IDEs), desktop applications, and everything in between.",
                    "profiles": {
                        "java": [
                            "eclipse-equinox-osgi",
                            "eclipse-jdt",
                            "eclipse-pde",
                            "eclipse-platform",
                            "eclipse-swt",
                        ]
                    },
                }
            ],
        },
        {
            "module_name": "idm",
            "streams": [
                {
                    "name": "idm",
                    "stream": "client",
                    "context": "49cc9d1b",
                    "arch": "x86_64",
                    "version": "820190227213458",
                    "description": "RHEL IdM is an integrated solution to provide centrally managed Identity (users, hosts, services), Authentication (SSO, 2FA), and Authorization (host access control, SELinux user roles, services). The solution provides features for further integration with Linux based clients (SUDO, automount) and integration with Active Directory based infrastructures (Trusts).\nThis module stream supports only client side of RHEL IdM solution",
                    "profiles": {"common": ["ipa-client"]},
                },
                {
                    "name": "idm",
                    "stream": "DL1",
                    "context": "5986f621",
                    "arch": "x86_64",
                    "version": "820190227212412",
                    "description": "RHEL IdM is an integrated solution to provide centrally managed Identity (users, hosts, services), Authentication (SSO, 2FA), and Authorization (host access control, SELinux user roles, services). The solution provides features for further integration with Linux based clients (SUDO, automount) and integration with Active Directory based infrastructures (Trusts).",
                    "profiles": {
                        "adtrust": ["ipa-idoverride-memberof-plugin", "ipa-server-trust-ad"],
                        "client": ["ipa-client"],
                        "common": ["ipa-client"],
                        "dns": ["ipa-server", "ipa-server-dns"],
                        "server": ["ipa-server"],
                    },
                },
            ],
        },
        {
            "module_name": "python36",
            "streams": [
                {
                    "name": "python36",
                    "stream": "3.6",
                    "context": "17efdbc7",
                    "arch": "x86_64",
                    "version": "820190123171828",
                    "description": "This module gives users access to the internal Python 3.6 in RHEL8, as\nwell as provides some additional Python packages the users might need.\nIn addition to these you can install any python3-* package available\nin RHEL and use it with Python from this module.",
                    "profiles": {
                        "build": ["python36", "python36-devel", "python36-rpm-macros"],
                        "common": ["python36"],
                    },
                }
            ],
        },
        {
            "module_name": "httpd",
            "streams": [
                {
                    "name": "httpd",
                    "stream": "2.4",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820190206142837",
                    "description": "Apache httpd is a powerful, efficient, and extensible HTTP server.",
                    "profiles": {
                        "common": ["httpd", "httpd-filesystem", "httpd-tools", "mod_http2", "mod_ssl"],
                        "devel": ["httpd", "httpd-devel", "httpd-filesystem", "httpd-tools"],
                        "minimal": ["httpd"],
                    },
                }
            ],
        },
        {
            "module_name": "perl-libwww-perl",
            "streams": [
                {
                    "name": "perl-libwww-perl",
                    "stream": "6.34",
                    "context": "b947e2fe",
                    "arch": "x86_64",
                    "version": "8060020210901111951",
                    "description": "The libwww-perl collection is a set of Perl modules which provide a simple and consistent application programming interface to the World-Wide Web. The main focus of the library is to provide classes and functions that enable you to write WWW clients. The library also contains modules that are of more general use and even classes that help you implement simple HTTP servers. LWP::Protocol::https adds a support for an HTTPS protocol.\n",
                    "profiles": {"common": ["perl-LWP-Protocol-https", "perl-libwww-perl"]},
                }
            ],
        },
        {
            "module_name": "jmc",
            "streams": [
                {
                    "name": "jmc",
                    "stream": "rhel8",
                    "context": "6392b1f8",
                    "arch": "x86_64",
                    "version": "8050020211005144542",
                    "description": "Java Mission Control is a powerful profiler for HotSpot JVMs and has an advanced set of tools that enables efficient and detailed analysis of the extensive data collected by Java Flight Recorder. The tool chain enables developers and administrators to collect and analyze data from Java applications running locally or deployed in production environments.",
                    "profiles": {"common": ["jmc"], "core": ["jmc-core"]},
                }
            ],
        },
        {
            "module_name": "mailman",
            "streams": [
                {
                    "name": "mailman",
                    "stream": "2.1",
                    "context": "77fc8825",
                    "arch": "x86_64",
                    "version": "820181213140247",
                    "description": "An initial version of the mailman mailing list management software",
                    "profiles": {"common": ["mailman"]},
                }
            ],
        },
        {
            "module_name": "perl-DBD-MySQL",
            "streams": [
                {
                    "name": "perl-DBD-MySQL",
                    "stream": "4.046",
                    "context": "6bc6cad6",
                    "arch": "x86_64",
                    "version": "820181214121012",
                    "description": "DBD::mysql is the Perl5 Database Interface driver for the MySQL database. In other words: DBD::mysql is an interface between the Perl programming language and the MySQL programming API that comes with the MySQL relational database management system.\n",
                    "profiles": {"common": ["perl-DBD-MySQL"]},
                }
            ],
        },
        {
            "module_name": "redis",
            "streams": [
                {
                    "name": "redis",
                    "stream": "5",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820181217094919",
                    "description": "redis 5 module",
                    "profiles": {"common": ["redis"]},
                },
                {
                    "name": "redis",
                    "stream": "6",
                    "context": "3b9f49c4",
                    "arch": "x86_64",
                    "version": "8070020220509142426",
                    "description": "redis 6 module",
                    "profiles": {"common": ["redis"]},
                },
            ],
        },
        {
            "module_name": "389-ds",
            "streams": [
                {
                    "name": "389-ds",
                    "stream": "1.4",
                    "context": "1fc8b219",
                    "arch": "x86_64",
                    "version": "820190201170147",
                    "description": "389 Directory Server is an LDAPv3 compliant server.  The base package includes the LDAP server and command line utilities for server administration.",
                    "profiles": {},
                }
            ],
        },
        {
            "module_name": "ant",
            "streams": [
                {
                    "name": "ant",
                    "stream": "1.1",
                    "context": "5ea3b708",
                    "arch": "x86_64",
                    "version": "820181213135032",
                    "description": "Apache Ant is a Java library and command-line tool whose mission is to drive processes described in build files as targets and extension points dependent upon each other. The main known usage of Ant is the build of Java applications. Ant supplies a number of built-in tasks allowing to compile, assemble, test and run Java applications. Ant can also be used effectively to build non Java applications, for instance C or C++ applications. More generally, Ant can be used to pilot any type of process which can be described in terms of targets and tasks.",
                    "profiles": {"common": ["ant"]},
                },
                {
                    "name": "ant",
                    "stream": "1.10",
                    "context": "417e5c08",
                    "arch": "x86_64",
                    "version": "8100020240221104459",
                    "description": "Apache Ant is a Java library and command-line tool whose mission is to drive processes described in build files as targets and extension points dependent upon each other. The main known usage of Ant is the build of Java applications. Ant supplies a number of built-in tasks allowing to compile, assemble, test and run Java applications. Ant can also be used effectively to build non Java applications, for instance C or C++ applications. More generally, Ant can be used to pilot any type of process which can be described in terms of targets and tasks.",
                    "profiles": {"common": ["ant"]},
                },
            ],
        },
        {
            "module_name": "mod_auth_openidc",
            "streams": [
                {
                    "name": "mod_auth_openidc",
                    "stream": "2.3",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820181213140451",
                    "description": "This module enables an Apache 2.x web server to operate as an OpenID Connect Relying Party and/or OAuth 2.0 Resource Server.",
                    "profiles": {},
                }
            ],
        },
        {
            "module_name": "nodejs",
            "streams": [
                {
                    "name": "nodejs",
                    "stream": "10",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820190108092226",
                    "description": "Node.js is a platform built on Chrome's JavaScript runtime for easily building fast, scalable network applications. Node.js uses an event-driven, non-blocking I/O model that makes it lightweight and efficient, perfect for data-intensive real-time applications that run across distributed devices.",
                    "profiles": {
                        "common": ["nodejs", "npm"],
                        "development": ["nodejs", "nodejs-devel", "npm"],
                        "minimal": ["nodejs"],
                        "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                    },
                },
                {
                    "name": "nodejs",
                    "stream": "12",
                    "context": "ad008a3a",
                    "arch": "x86_64",
                    "version": "8060020220523160029",
                    "description": "Node.js is a platform built on Chrome's JavaScript runtime for easily building fast, scalable network applications. Node.js uses an event-driven, non-blocking I/O model that makes it lightweight and efficient, perfect for data-intensive real-time applications that run across distributed devices.",
                    "profiles": {
                        "common": ["nodejs", "npm"],
                        "development": ["nodejs", "nodejs-devel", "npm"],
                        "minimal": ["nodejs"],
                        "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                    },
                },
                {
                    "name": "nodejs",
                    "stream": "14",
                    "context": "bd1311ed",
                    "arch": "x86_64",
                    "version": "8070020230306170042",
                    "description": "Node.js is a platform built on Chrome's JavaScript runtime for easily building fast, scalable network applications. Node.js uses an event-driven, non-blocking I/O model that makes it lightweight and efficient, perfect for data-intensive real-time applications that run across distributed devices.",
                    "profiles": {
                        "common": ["nodejs", "npm"],
                        "development": ["nodejs", "nodejs-devel", "npm"],
                        "minimal": ["nodejs"],
                        "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                    },
                },
                {
                    "name": "nodejs",
                    "stream": "16",
                    "context": "a75119d5",
                    "arch": "x86_64",
                    "version": "8090020240315081818",
                    "description": "Node.js is a platform built on Chrome's JavaScript runtime for easily building fast, scalable network applications. Node.js uses an event-driven, non-blocking I/O model that makes it lightweight and efficient, perfect for data-intensive real-time applications that run across distributed devices.",
                    "profiles": {
                        "common": ["nodejs", "npm"],
                        "development": ["nodejs", "nodejs-devel", "npm"],
                        "minimal": ["nodejs"],
                        "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                    },
                },
                {
                    "name": "nodejs",
                    "stream": "18",
                    "context": "489197000000",
                    "arch": "x86_64",
                    "version": "8100020240807161023",
                    "description": "Node.js is a platform built on Chrome's JavaScript runtime for easily building fast, scalable network applications. Node.js uses an event-driven, non-blocking I/O model that makes it lightweight and efficient, perfect for data-intensive real-time applications that run across distributed devices.",
                    "profiles": {
                        "common": ["nodejs", "npm"],
                        "development": ["nodejs", "nodejs-devel", "npm"],
                        "minimal": ["nodejs"],
                        "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                    },
                },
                {
                    "name": "nodejs",
                    "stream": "20",
                    "context": "489197000000",
                    "arch": "x86_64",
                    "version": "8100020240808073736",
                    "description": "Node.js is a platform built on Chrome's JavaScript runtime for easily building fast, scalable network applications. Node.js uses an event-driven, non-blocking I/O model that makes it lightweight and efficient, perfect for data-intensive real-time applications that run across distributed devices.",
                    "profiles": {
                        "common": ["nodejs", "npm"],
                        "development": ["nodejs", "nodejs-devel", "npm"],
                        "minimal": ["nodejs"],
                        "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                    },
                },
            ],
        },
        {
            "module_name": "php",
            "streams": [
                {
                    "name": "php",
                    "stream": "7.2",
                    "context": "765540",
                    "arch": "x86_64",
                    "version": "820181215112050",
                    "description": "php 7.2 module",
                    "profiles": {
                        "common": ["php-cli", "php-common", "php-fpm", "php-json", "php-mbstring", "php-xml"],
                        "devel": [
                            "libzip",
                            "php-cli",
                            "php-common",
                            "php-devel",
                            "php-fpm",
                            "php-json",
                            "php-mbstring",
                            "php-pear",
                            "php-pecl-zip",
                            "php-process",
                            "php-xml",
                        ],
                        "minimal": ["php-cli", "php-common"],
                    },
                },
                {
                    "name": "php",
                    "stream": "7.3",
                    "context": "ceb1cf90",
                    "arch": "x86_64",
                    "version": "8020020200715124551",
                    "description": "php 7.3 module",
                    "profiles": {
                        "common": ["php-cli", "php-common", "php-fpm", "php-json", "php-mbstring", "php-xml"],
                        "devel": [
                            "libzip",
                            "php-cli",
                            "php-common",
                            "php-devel",
                            "php-fpm",
                            "php-json",
                            "php-mbstring",
                            "php-pear",
                            "php-pecl-zip",
                            "php-process",
                            "php-xml",
                        ],
                        "minimal": ["php-cli", "php-common"],
                    },
                },
                {
                    "name": "php",
                    "stream": "7.4",
                    "context": "f7998665",
                    "arch": "x86_64",
                    "version": "8100020241113075828",
                    "description": "php 7.4 module",
                    "profiles": {
                        "common": ["php-cli", "php-common", "php-fpm", "php-json", "php-mbstring", "php-xml"],
                        "devel": [
                            "libzip",
                            "php-cli",
                            "php-common",
                            "php-devel",
                            "php-fpm",
                            "php-json",
                            "php-mbstring",
                            "php-pear",
                            "php-pecl-zip",
                            "php-process",
                            "php-xml",
                        ],
                        "minimal": ["php-cli", "php-common"],
                    },
                },
                {
                    "name": "php",
                    "stream": "8.0",
                    "context": "0b4eb31d",
                    "arch": "x86_64",
                    "version": "8080020231006102311",
                    "description": "php 8.0 module",
                    "profiles": {
                        "common": ["php-cli", "php-common", "php-fpm", "php-mbstring", "php-xml"],
                        "devel": [
                            "libzip",
                            "php-cli",
                            "php-common",
                            "php-devel",
                            "php-fpm",
                            "php-mbstring",
                            "php-pear",
                            "php-pecl-zip",
                            "php-process",
                            "php-xml",
                        ],
                        "minimal": ["php-cli", "php-common"],
                    },
                },
                {
                    "name": "php",
                    "stream": "8.2",
                    "context": "f7998665",
                    "arch": "x86_64",
                    "version": "8100020241112130045",
                    "description": "php 8.2 module",
                    "profiles": {
                        "common": ["php-cli", "php-common", "php-fpm", "php-mbstring", "php-xml"],
                        "devel": [
                            "libzip",
                            "php-cli",
                            "php-common",
                            "php-devel",
                            "php-fpm",
                            "php-mbstring",
                            "php-pear",
                            "php-pecl-zip",
                            "php-process",
                            "php-xml",
                        ],
                        "minimal": ["php-cli", "php-common"],
                    },
                },
            ],
        },
        {
            "module_name": "ruby",
            "streams": [
                {
                    "name": "ruby",
                    "stream": "2.5",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820190111110530",
                    "description": "Ruby is the interpreted scripting language for quick and easy object-oriented programming.  It has many features to process text files and to do system management tasks (as in Perl).  It is simple, straight-forward, and extensible.",
                    "profiles": {"common": ["ruby"]},
                },
                {
                    "name": "ruby",
                    "stream": "2.6",
                    "context": "ad008a3a",
                    "arch": "x86_64",
                    "version": "8060020220527104428",
                    "description": "Ruby is the interpreted scripting language for quick and easy object-oriented programming.  It has many features to process text files and to do system management tasks (as in Perl).  It is simple, straight-forward, and extensible.",
                    "profiles": {"common": ["ruby"]},
                },
                {
                    "name": "ruby",
                    "stream": "2.7",
                    "context": "63b34585",
                    "arch": "x86_64",
                    "version": "8080020230427102918",
                    "description": "Ruby is the interpreted scripting language for quick and easy object-oriented programming.  It has many features to process text files and to do system management tasks (as in Perl).  It is simple, straight-forward, and extensible.",
                    "profiles": {"common": ["ruby"]},
                },
                {
                    "name": "ruby",
                    "stream": "3.0",
                    "context": "489197000000",
                    "arch": "x86_64",
                    "version": "8100020240522072634",
                    "description": "Ruby is the interpreted scripting language for quick and easy object-oriented programming.  It has many features to process text files and to do system management tasks (as in Perl).  It is simple, straight-forward, and extensible.",
                    "profiles": {"common": ["ruby"]},
                },
                {
                    "name": "ruby",
                    "stream": "3.1",
                    "context": "489197000000",
                    "arch": "x86_64",
                    "version": "8100020241127152928",
                    "description": "Ruby is the interpreted scripting language for quick and easy object-oriented programming.  It has many features to process text files and to do system management tasks (as in Perl).  It is simple, straight-forward, and extensible.",
                    "profiles": {"common": ["ruby"]},
                },
                {
                    "name": "ruby",
                    "stream": "3.3",
                    "context": "489197000000",
                    "arch": "x86_64",
                    "version": "8100020240906074654",
                    "description": "Ruby is the interpreted scripting language for quick and easy object-oriented programming.  It has many features to process text files and to do system management tasks (as in Perl).  It is simple, straight-forward, and extensible.",
                    "profiles": {"common": ["ruby"]},
                },
            ],
        },
        {
            "module_name": "gimp",
            "streams": [
                {
                    "name": "gimp",
                    "stream": "2.8",
                    "context": "77fc8825",
                    "arch": "x86_64",
                    "version": "820181213135540",
                    "description": "GIMP (GNU Image Manipulation Program) is a powerful image composition and\nediting program, which can be extremely useful for creating logos and other\ngraphics for webpages. ",
                    "profiles": {"common": ["gimp"], "devel": ["gimp-devel", "gimp-devel-tools"]},
                }
            ],
        },
        {
            "module_name": "mariadb",
            "streams": [
                {
                    "name": "mariadb",
                    "stream": "10.11",
                    "context": "e155f54d",
                    "arch": "x86_64",
                    "version": "8100020240129174731",
                    "description": "MariaDB is a community developed branch of MySQL. MariaDB is a multi-user, multi-threaded SQL database server. It is a client/server implementation consisting of a server daemon (mysqld) and many different client programs and libraries. The base package contains the standard MariaDB/MySQL client programs and generic MySQL files.",
                    "profiles": {
                        "client": ["mariadb"],
                        "galera": ["mariadb-server", "mariadb-server-galera"],
                        "server": ["mariadb-server"],
                    },
                },
                {
                    "name": "mariadb",
                    "stream": "10.3",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820190314153642",
                    "description": "MariaDB is a community developed branch of MySQL. MariaDB is a multi-user, multi-threaded SQL database server. It is a client/server implementation consisting of a server daemon (mysqld) and many different client programs and libraries. The base package contains the standard MariaDB/MySQL client programs and generic MySQL files.",
                    "profiles": {
                        "client": ["mariadb"],
                        "galera": ["mariadb-server", "mariadb-server-galera"],
                        "server": ["mariadb-server"],
                    },
                },
                {
                    "name": "mariadb",
                    "stream": "10.5",
                    "context": "63b34585",
                    "arch": "x86_64",
                    "version": "8080020231003163755",
                    "description": "MariaDB is a community developed branch of MySQL. MariaDB is a multi-user, multi-threaded SQL database server. It is a client/server implementation consisting of a server daemon (mysqld) and many different client programs and libraries. The base package contains the standard MariaDB/MySQL client programs and generic MySQL files.",
                    "profiles": {
                        "client": ["mariadb"],
                        "galera": ["mariadb-server", "mariadb-server-galera"],
                        "server": ["mariadb-server"],
                    },
                },
            ],
        },
        {
            "module_name": "scala",
            "streams": [
                {
                    "name": "scala",
                    "stream": "2.1",
                    "context": "2b79a98f",
                    "arch": "x86_64",
                    "version": "820181213143541",
                    "description": "Scala is a general purpose programming language designed to express common programming patterns in a concise, elegant, and type-safe way. It smoothly integrates features of object-oriented and functional languages. It is also fully interoperable with Java.",
                    "profiles": {"common": ["scala"]},
                }
            ],
        },
        {
            "module_name": "perl-YAML",
            "streams": [
                {
                    "name": "perl-YAML",
                    "stream": "1.24",
                    "context": "8652dbeb",
                    "arch": "x86_64",
                    "version": "820181214175558",
                    "description": "The YAML.pm module implements a YAML Loader and Dumper based on the YAML 1.0 specification. YAML is a generic data serialization language that is optimized for human readability. It can be used to express the data structures of most modern programming languages, including Perl. For information on the YAML syntax, please refer to the YAML specification.\n",
                    "profiles": {"common": ["perl-YAML"]},
                }
            ],
        },
        {
            "module_name": "javapackages-runtime",
            "streams": [
                {
                    "name": "javapackages-runtime",
                    "stream": "201801",
                    "context": "302ab70f",
                    "arch": "x86_64",
                    "version": "820181213140046",
                    "description": "This module contains basic filesystem layout and runtime utilities used to support system applications written in JVM languages.",
                    "profiles": {"common": ["javapackages-filesystem", "javapackages-tools"]},
                }
            ],
        },
        {
            "module_name": "perl",
            "streams": [
                {
                    "name": "perl",
                    "stream": "5.24",
                    "context": "ee766497",
                    "arch": "x86_64",
                    "version": "820190207164249",
                    "description": "Perl is a high-level programming language with roots in C, sed, awk and shell scripting. Perl is good at handling processes and files, and is especially good at handling text. Perl's hallmarks are practicality and efficiency. While it is used to do a lot of different things, Perl's most common applications are system administration utilities and web programming.\n",
                    "profiles": {"common": ["perl-core"], "minimal": ["perl"]},
                },
                {
                    "name": "perl",
                    "stream": "5.26",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820181219174508",
                    "description": "Perl is a high-level programming language with roots in C, sed, awk and shell scripting. Perl is good at handling processes and files, and is especially good at handling text. Perl's hallmarks are practicality and efficiency. While it is used to do a lot of different things, Perl's most common applications are system administration utilities and web programming.\n",
                    "profiles": {"common": ["perl"], "minimal": ["perl-interpreter"]},
                },
                {
                    "name": "perl",
                    "stream": "5.3",
                    "context": "466ea64f",
                    "arch": "x86_64",
                    "version": "8040020200923213406",
                    "description": "Perl is a high-level programming language with roots in C, sed, awk and shell scripting. Perl is good at handling processes and files, and is especially good at handling text. Perl's hallmarks are practicality and efficiency. While it is used to do a lot of different things, Perl's most common applications are system administration utilities and web programming.\n",
                    "profiles": {"common": ["perl"], "minimal": ["perl-interpreter"]},
                },
                {
                    "name": "perl",
                    "stream": "5.32",
                    "context": "9fe1d287",
                    "arch": "x86_64",
                    "version": "8100020240314121426",
                    "description": "Perl is a high-level programming language with roots in C, sed, awk and shell scripting. Perl is good at handling processes and files, and is especially good at handling text. Perl's hallmarks are practicality and efficiency. While it is used to do a lot of different things, Perl's most common applications are system administration utilities and web programming.\n",
                    "profiles": {"common": ["perl"], "minimal": ["perl-interpreter"]},
                },
            ],
        },
        {
            "module_name": "inkscape",
            "streams": [
                {
                    "name": "inkscape",
                    "stream": "0.92.3",
                    "context": "77fc8825",
                    "arch": "x86_64",
                    "version": "820181213140018",
                    "description": "Inkscape is a vector graphics editor, with capabilities similar to\nIllustrator, CorelDraw, or Xara X, using the W3C standard Scalable Vector\nGraphics (SVG) file format.  It is therefore a very useful tool for web\ndesigners and as an interchange format for desktop publishing.\n\nInkscape supports many advanced SVG features (markers, clones, alpha\nblending, etc.) and great care is taken in designing a streamlined\ninterface. It is very easy to edit nodes, perform complex path operations,\ntrace bitmaps and much more.",
                    "profiles": {"common": ["inkscape"]},
                }
            ],
        },
        {
            "module_name": "mercurial",
            "streams": [
                {
                    "name": "mercurial",
                    "stream": "4.8",
                    "context": "77fc8825",
                    "arch": "x86_64",
                    "version": "820190108205035",
                    "description": "Mercurial is a fast, lightweight source control management system designed for efficient handling of very large distributed projects.",
                    "profiles": {"common": ["mercurial"]},
                },
                {
                    "name": "mercurial",
                    "stream": "6.2",
                    "context": "3dbb8329",
                    "arch": "x86_64",
                    "version": "8070020220729131051",
                    "description": "Mercurial is a fast, lightweight source control management system designed for efficient handling of very large distributed projects.",
                    "profiles": {"common": ["mercurial"]},
                },
            ],
        },
        {
            "module_name": "perl-App-cpanminus",
            "streams": [
                {
                    "name": "perl-App-cpanminus",
                    "stream": "1.7044",
                    "context": "e5ce1481",
                    "arch": "x86_64",
                    "version": "820181214184336",
                    "description": "This is a CPAN client that requires zero configuration, and stands alone but it's maintainable and extensible with plug-ins and friendly to shell scripting.\n",
                    "profiles": {"common": ["perl-App-cpanminus"]},
                }
            ],
        },
        {
            "module_name": "container-tools",
            "streams": [
                {
                    "name": "container-tools",
                    "stream": "1",
                    "context": "20125149",
                    "arch": "x86_64",
                    "version": "820190220135513",
                    "description": "Contains SELinux policies, binaries and other dependencies for use with container runtimes",
                    "profiles": {
                        "common": [
                            "buildah",
                            "container-selinux",
                            "containernetworking-plugins",
                            "fuse-overlayfs",
                            "oci-systemd-hook",
                            "oci-umount",
                            "podman",
                            "runc",
                            "skopeo",
                            "slirp4netns",
                        ]
                    },
                },
                {
                    "name": "container-tools",
                    "stream": "2",
                    "context": "830d479e",
                    "arch": "x86_64",
                    "version": "8030020210302075156",
                    "description": "Stable versions of podman 1.6, buildah 1.11, skopeo 0.1, runc, conmon, CRIU, Udica, etc as well as dependencies such as container-selinux built and tested together. Released with RHEL 8.2 and supported for 24 months. During the support lifecycle, back ports of important, critical vulnerabilities (CVEs, RHSAs) and bug fixes (RHBAs) are provided to this stream, and versions do not move forward. For more information see: https://access.redhat.com/support/policy/updates/containertools",
                    "profiles": {
                        "common": [
                            "buildah",
                            "cockpit-podman",
                            "conmon",
                            "container-selinux",
                            "containernetworking-plugins",
                            "criu",
                            "fuse-overlayfs",
                            "podman",
                            "python-podman-api",
                            "runc",
                            "skopeo",
                            "slirp4netns",
                            "toolbox",
                            "udica",
                        ]
                    },
                },
                {
                    "name": "container-tools",
                    "stream": "2.0",
                    "context": "e34216c9",
                    "arch": "x86_64",
                    "version": "8050020220411114323",
                    "description": "Stable versions of podman 1.6, buildah 1.11, skopeo 0.1, runc, conmon, CRIU, Udica, etc as well as dependencies such as container-selinux built and tested together. Released with RHEL 8.2 and supported for 24 months. During the support lifecycle, back ports of important, critical vulnerabilities (CVEs, RHSAs) and bug fixes (RHBAs) are provided to this stream, and versions do not move forward. For more information see: https://access.redhat.com/support/policy/updates/containertools",
                    "profiles": {
                        "common": [
                            "buildah",
                            "cockpit-podman",
                            "conmon",
                            "container-selinux",
                            "containernetworking-plugins",
                            "criu",
                            "fuse-overlayfs",
                            "podman",
                            "python-podman-api",
                            "runc",
                            "skopeo",
                            "slirp4netns",
                            "toolbox",
                            "udica",
                        ]
                    },
                },
                {
                    "name": "container-tools",
                    "stream": "3.0",
                    "context": "489fc8e9",
                    "arch": "x86_64",
                    "version": "8070020230131134905",
                    "description": "Stable versions of podman 3.0, buildah 1.19, skopeo 1.2, runc, conmon, CRIU, Udica, etc as well as dependencies such as container-selinux built and tested together. Released with RHEL 8.4 and supported for 24 months. During the support lifecycle, back ports of important, critical vulnerabilities (CVEs, RHSAs) and bug fixes (RHBAs) are provided to this stream, and versions do not move forward. For more information see: https://access.redhat.com/support/policy/updates/containertools",
                    "profiles": {
                        "common": [
                            "buildah",
                            "cockpit-podman",
                            "conmon",
                            "container-selinux",
                            "containernetworking-plugins",
                            "criu",
                            "crun",
                            "fuse-overlayfs",
                            "libslirp",
                            "podman",
                            "runc",
                            "skopeo",
                            "slirp4netns",
                            "toolbox",
                            "udica",
                        ]
                    },
                },
                {
                    "name": "container-tools",
                    "stream": "4.0",
                    "context": "d7b6f4b7",
                    "arch": "x86_64",
                    "version": "8090020240413110917",
                    "description": "Stable versions of podman 4.0, buildah 1.24, skopeo 1.6, runc, conmon, CRIU, Udica, etc as well as dependencies such as container-selinux built and tested together. Released with RHEL 8.6 and supported for 24 months. During the support lifecycle, back ports of important, critical vulnerabilities (CVEs, RHSAs) and bug fixes (RHBAs) are provided to this stream, and versions do not move forward. For more information see: https://access.redhat.com/support/policy/updates/containertools",
                    "profiles": {
                        "common": [
                            "buildah",
                            "cockpit-podman",
                            "conmon",
                            "container-selinux",
                            "containernetworking-plugins",
                            "containers-common",
                            "criu",
                            "crun",
                            "fuse-overlayfs",
                            "libslirp",
                            "podman",
                            "python3-podman",
                            "runc",
                            "skopeo",
                            "slirp4netns",
                            "toolbox",
                            "udica",
                        ]
                    },
                },
                {
                    "name": "container-tools",
                    "stream": "rhel8",
                    "context": "20125149",
                    "arch": "x86_64",
                    "version": "820190211172150",
                    "description": "Contains SELinux policies, binaries and other dependencies for use with container runtimes",
                    "profiles": {
                        "common": [
                            "buildah",
                            "container-selinux",
                            "containernetworking-plugins",
                            "fuse-overlayfs",
                            "oci-systemd-hook",
                            "oci-umount",
                            "podman",
                            "runc",
                            "skopeo",
                            "slirp4netns",
                        ]
                    },
                },
            ],
        },
        {
            "module_name": "freeradius",
            "streams": [
                {
                    "name": "freeradius",
                    "stream": "3",
                    "context": "fbe42456",
                    "arch": "x86_64",
                    "version": "820190131191847",
                    "description": "The FreeRADIUS Server Project is a high performance and highly configurable GPL'd free RADIUS server. The server is similar in some respects to Livingston's 2.0 server.  While FreeRADIUS started as a variant of the Cistron RADIUS server, they don't share a lot in common any more. It now has many more features than Cistron or Livingston, and is much more configurable.\nFreeRADIUS is an Internet authentication daemon, which implements the RADIUS protocol, as defined in RFC 2865 (and others). It allows Network Access Servers (NAS boxes) to perform authentication for dial-up users. There are also RADIUS clients available for Web servers, firewalls, Unix logins, and more.  Using RADIUS allows authentication and authorization for a network to be centralized, and minimizes the amount of re-configuration which has to be done when adding or deleting new users.",
                    "profiles": {"server": ["freeradius"]},
                },
                {
                    "name": "freeradius",
                    "stream": "3.0",
                    "context": "69ef70f8",
                    "arch": "x86_64",
                    "version": "8100020230904084920",
                    "description": "The FreeRADIUS Server Project is a high performance and highly configurable GPL'd free RADIUS server. The server is similar in some respects to Livingston's 2.0 server.  While FreeRADIUS started as a variant of the Cistron RADIUS server, they don't share a lot in common any more. It now has many more features than Cistron or Livingston, and is much more configurable.\nFreeRADIUS is an Internet authentication daemon, which implements the RADIUS protocol, as defined in RFC 2865 (and others). It allows Network Access Servers (NAS boxes) to perform authentication for dial-up users. There are also RADIUS clients available for Web servers, firewalls, Unix logins, and more.  Using RADIUS allows authentication and authorization for a network to be centralized, and minimizes the amount of re-configuration which has to be done when adding or deleting new users.",
                    "profiles": {"server": ["freeradius"]},
                },
            ],
        },
        {
            "module_name": "virt",
            "streams": [
                {
                    "name": "virt",
                    "stream": "rhel",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820190226174025",
                    "description": "A virtualization module",
                    "profiles": {
                        "common": [
                            "libguestfs",
                            "libvirt-client",
                            "libvirt-daemon-config-network",
                            "libvirt-daemon-kvm",
                        ]
                    },
                }
            ],
        },
        {
            "module_name": "maven",
            "streams": [
                {
                    "name": "maven",
                    "stream": "3.5",
                    "context": "5ea3b708",
                    "arch": "x86_64",
                    "version": "820181213140354",
                    "description": "Maven is a software project management and comprehension tool. Based on the concept of a project object model (POM), Maven can manage a project's build, reporting and documentation from a central piece of information.",
                    "profiles": {"common": ["maven"]},
                },
                {
                    "name": "maven",
                    "stream": "3.6",
                    "context": "9d367344",
                    "arch": "x86_64",
                    "version": "8080020230202141236",
                    "description": "Maven is a software project management and comprehension tool. Based on the concept of a project object model (POM), Maven can manage a project's build, reporting and documentation from a central piece of information.",
                    "profiles": {"common": ["maven-openjdk11"]},
                },
                {
                    "name": "maven",
                    "stream": "3.8",
                    "context": "9b3be2c4",
                    "arch": "x86_64",
                    "version": "8100020240210094037",
                    "description": "Maven is a software project management and comprehension tool. Based on the concept of a project object model (POM), Maven can manage a project's build, reporting and documentation from a central piece of information.",
                    "profiles": {"common": ["maven-openjdk11"]},
                },
            ],
        },
        {
            "module_name": "pki-deps",
            "streams": [
                {
                    "name": "pki-deps",
                    "stream": "10.6",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820190223041344",
                    "description": "A module for PKI dependencies.",
                    "profiles": {},
                }
            ],
        },
        {
            "module_name": "perl-DBD-Pg",
            "streams": [
                {
                    "name": "perl-DBD-Pg",
                    "stream": "3.7",
                    "context": "956b9ee3",
                    "arch": "x86_64",
                    "version": "820181214121102",
                    "description": "DBD::Pg is a Perl module that works with the DBI module to provide access to PostgreSQL databases.\n",
                    "profiles": {"common": ["perl-DBD-Pg"]},
                }
            ],
        },
        {
            "module_name": "squid",
            "streams": [
                {
                    "name": "squid",
                    "stream": "4",
                    "context": "9edba152",
                    "arch": "x86_64",
                    "version": "820181213143653",
                    "description": "an initial version of the squid caching proxy module",
                    "profiles": {"common": ["squid"]},
                }
            ],
        },
        {
            "module_name": "libselinux-python",
            "streams": [
                {
                    "name": "libselinux-python",
                    "stream": "2.8",
                    "context": "77fc8825",
                    "arch": "x86_64",
                    "version": "820181213140134",
                    "description": "The libselinux-python package contains the python bindings for developing SELinux applications.",
                    "profiles": {"common": ["libselinux-python"]},
                }
            ],
        },
        {
            "module_name": "parfait",
            "streams": [
                {
                    "name": "parfait",
                    "stream": "0.5",
                    "context": "d2b614b2",
                    "arch": "x86_64",
                    "version": "820181213142511",
                    "description": "Parfait is a Java performance monitoring library that exposes and collects metrics through a variety of outputs.  It provides APIs for extracting performance metrics from the JVM and other sources. It interfaces to Performance Co-Pilot (PCP) using the Memory Mapped Value (MMV) machinery for extremely lightweight instrumentation.",
                    "profiles": {"common": ["parfait", "parfait-examples", "pcp-parfait-agent"]},
                }
            ],
        },
    ],
    9: [
        {
            "module_name": "nginx",
            "streams": [
                {
                    "name": "nginx",
                    "stream": "1.22",
                    "context": "9",
                    "arch": "x86_64",
                    "version": "9050020240717000135",
                    "description": "nginx 1.22 webserver module",
                    "profiles": {
                        "common": [
                            "nginx",
                            "nginx-all-modules",
                            "nginx-filesystem",
                            "nginx-mod-http-image-filter",
                            "nginx-mod-http-perl",
                            "nginx-mod-http-xslt-filter",
                            "nginx-mod-mail",
                            "nginx-mod-stream",
                        ]
                    },
                },
                {
                    "name": "nginx",
                    "stream": "1.24",
                    "context": "9",
                    "arch": "x86_64",
                    "version": "9050020240717000500",
                    "description": "nginx 1.24 webserver module",
                    "profiles": {
                        "common": [
                            "nginx",
                            "nginx-all-modules",
                            "nginx-filesystem",
                            "nginx-mod-http-image-filter",
                            "nginx-mod-http-perl",
                            "nginx-mod-http-xslt-filter",
                            "nginx-mod-mail",
                            "nginx-mod-stream",
                        ]
                    },
                },
            ],
        },
        {
            "module_name": "nodejs",
            "streams": [
                {
                    "name": "nodejs",
                    "stream": "18",
                    "context": "rhel9",
                    "arch": "x86_64",
                    "version": "9040020240807131341",
                    "description": "Node.js is a platform built on Chrome's JavaScript runtime for easily building fast, scalable network applications. Node.js uses an event-driven, non-blocking I/O model that makes it lightweight and efficient, perfect for data-intensive real-time applications that run across distributed devices.",
                    "profiles": {
                        "common": ["nodejs", "npm"],
                        "development": ["nodejs", "nodejs-devel", "npm"],
                        "minimal": ["nodejs"],
                        "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                    },
                },
                {
                    "name": "nodejs",
                    "stream": "20",
                    "context": "rhel9",
                    "arch": "x86_64",
                    "version": "9050020240923133857",
                    "description": "Node.js is a platform built on Chrome's JavaScript runtime for easily building fast, scalable network applications. Node.js uses an event-driven, non-blocking I/O model that makes it lightweight and efficient, perfect for data-intensive real-time applications that run across distributed devices.",
                    "profiles": {
                        "common": ["nodejs", "npm"],
                        "development": ["nodejs", "nodejs-devel", "npm"],
                        "minimal": ["nodejs"],
                        "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                    },
                },
                {
                    "name": "nodejs",
                    "stream": "22",
                    "context": "rhel9",
                    "arch": "x86_64",
                    "version": "9050020241113142151",
                    "description": "Node.js is a platform built on Chrome's JavaScript runtime for easily building fast, scalable network applications. Node.js uses an event-driven, non-blocking I/O model that makes it lightweight and efficient, perfect for data-intensive real-time applications that run across distributed devices.",
                    "profiles": {
                        "common": ["nodejs", "npm"],
                        "development": ["nodejs", "nodejs-devel", "npm"],
                        "minimal": ["nodejs"],
                        "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                    },
                },
            ],
        },
        {
            "module_name": "php",
            "streams": [
                {
                    "name": "php",
                    "stream": "8.1",
                    "context": "9",
                    "arch": "x86_64",
                    "version": "9050020241112144108",
                    "description": "php 8.1 module",
                    "profiles": {
                        "common": ["php-cli", "php-common", "php-fpm", "php-mbstring", "php-xml"],
                        "devel": [
                            "php-cli",
                            "php-common",
                            "php-devel",
                            "php-fpm",
                            "php-mbstring",
                            "php-pecl-zip",
                            "php-process",
                            "php-xml",
                        ],
                        "minimal": ["php-cli", "php-common"],
                    },
                },
                {
                    "name": "php",
                    "stream": "8.2",
                    "context": "9",
                    "arch": "x86_64",
                    "version": "9050020241112094217",
                    "description": "php 8.2 module",
                    "profiles": {
                        "common": ["php-cli", "php-common", "php-fpm", "php-mbstring", "php-xml"],
                        "devel": [
                            "php-cli",
                            "php-common",
                            "php-devel",
                            "php-fpm",
                            "php-mbstring",
                            "php-pecl-zip",
                            "php-process",
                            "php-xml",
                        ],
                        "minimal": ["php-cli", "php-common"],
                    },
                },
            ],
        },
        {
            "module_name": "postgresql",
            "streams": [
                {
                    "name": "postgresql",
                    "stream": "15",
                    "context": "rhel9",
                    "arch": "x86_64",
                    "version": "9050020241122141928",
                    "description": "PostgreSQL is an advanced Object-Relational database management system (DBMS). The postgresql-server package contains the programs needed to create and run a PostgreSQL server, which will in turn allow you to create and maintain PostgreSQL databases. The base postgresql package contains the client programs that you'll need to access a PostgreSQL DBMS server.",
                    "profiles": {"client": ["postgresql"], "server": ["postgresql-server"]},
                },
                {
                    "name": "postgresql",
                    "stream": "16",
                    "context": "rhel9",
                    "arch": "x86_64",
                    "version": "9050020241122142517",
                    "description": "PostgreSQL is an advanced Object-Relational database management system (DBMS). The postgresql-server package contains the programs needed to create and run a PostgreSQL server, which will in turn allow you to create and maintain PostgreSQL databases. The base postgresql package contains the client programs that you'll need to access a PostgreSQL DBMS server.",
                    "profiles": {"client": ["postgresql"], "server": ["postgresql-server"]},
                },
            ],
        },
        {
            "module_name": "redis",
            "streams": [
                {
                    "name": "redis",
                    "stream": "7",
                    "context": "9",
                    "arch": "x86_64",
                    "version": "9050020241104103753",
                    "description": "redis 7 module",
                    "profiles": {"common": ["redis"]},
                }
            ],
        },
        {
            "module_name": "ruby",
            "streams": [
                {
                    "name": "ruby",
                    "stream": "3.1",
                    "context": "9",
                    "arch": "x86_64",
                    "version": "9050020241127153348",
                    "description": "Ruby is the interpreted scripting language for quick and easy object-oriented programming.  It has many features to process text files and to do system management tasks (as in Perl).  It is simple, straight-forward, and extensible.",
                    "profiles": {"common": ["ruby"]},
                },
                {
                    "name": "ruby",
                    "stream": "3.3",
                    "context": "9",
                    "arch": "x86_64",
                    "version": "9040020240906110954",
                    "description": "Ruby is the interpreted scripting language for quick and easy object-oriented programming.  It has many features to process text files and to do system management tasks (as in Perl).  It is simple, straight-forward, and extensible.",
                    "profiles": {"common": ["ruby"]},
                },
            ],
        },
        {
            "module_name": "mariadb",
            "streams": [
                {
                    "name": "mariadb",
                    "stream": "10.11",
                    "context": "rhel9",
                    "arch": "x86_64",
                    "version": "9040020240126110506",
                    "description": "MariaDB is a community developed branch of MySQL. MariaDB is a multi-user, multi-threaded SQL database server. It is a client/server implementation consisting of a server daemon (mysqld) and many different client programs and libraries. The base package contains the standard MariaDB/MySQL client programs and generic MySQL files.",
                    "profiles": {
                        "client": ["mariadb"],
                        "galera": ["mariadb-server", "mariadb-server-galera"],
                        "server": ["mariadb-server"],
                    },
                }
            ],
        },
        {
            "module_name": "maven",
            "streams": [
                {
                    "name": "maven",
                    "stream": "3.8",
                    "context": "470dcefd",
                    "arch": "x86_64",
                    "version": "9040020240210002822",
                    "description": "Maven is a software project management and comprehension tool. Based on the concept of a project object model (POM), Maven can manage a project's build, reporting and documentation from a central piece of information.",
                    "profiles": {"common": ["maven-openjdk11"]},
                }
            ],
        },
    ],
}
