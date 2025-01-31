from datetime import date


MODULE_DATA = [
    {
        "module_name": "go-toolset",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "b754926a",
                "description": "Go Tools and libraries",
                "end_date": date(2019, 11, 30),
                "name": "go-toolset",
                "profiles": {"common": ["go-toolset"]},
                "start_date": date(2019, 5, 7),
                "stream": "rhel8",
                "version": "820190208025401",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "satellite-5-client",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "Red Hat Satellite 5 client packages provide "
                "programs and libraries to allow your system to "
                "receive software updates from Red Hat Satellite "
                "5.",
                "end_date": "Unknown",
                "name": "satellite-5-client",
                "profiles": {
                    "common": [
                        "dnf-plugin-spacewalk",
                        "rhn-client-tools",
                        "rhn-setup",
                        "rhnlib",
                        "rhnsd",
                    ],
                    "gui": [
                        "dnf-plugin-spacewalk",
                        "rhn-client-tools",
                        "rhn-setup",
                        "rhn-setup-gnome",
                        "rhnlib",
                        "rhnsd",
                    ],
                },
                "start_date": "Unknown",
                "stream": "1",
                "version": "820190204085912",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "swig",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "Simplified Wrapper and Interface Generator "
                "(SWIG) is a software development tool for "
                "connecting C, C++ and Objective C programs with "
                "a variety of high-level programming languages. "
                "SWIG is primarily used with Perl, Python and "
                "Tcl/TK, but it has also been extended to Java, "
                "Eiffel and Guile. SWIG is normally used to "
                "create high-level interpreted programming "
                "environments, systems integration, and as a "
                "tool for building user interfaces\n",
                "end_date": "Unknown",
                "name": "swig",
                "profiles": {
                    "common": ["swig"],
                    "complete": ["swig", "swig-doc", "swig-gdb"],
                },
                "start_date": "Unknown",
                "stream": "3",
                "version": "820181213143944",
            },
            {
                "arch": "x86_64",
                "context": "9f9e2e7e",
                "description": "Simplified Wrapper and Interface Generator "
                "(SWIG) is a software development tool for "
                "connecting C, C++ and Objective C programs with "
                "a variety of high-level programming languages. "
                "SWIG is primarily used with Perl, Python and "
                "Tcl/TK, but it has also been extended to Java, "
                "Eiffel and Guile. SWIG is normally used to "
                "create high-level interpreted programming "
                "environments, systems integration, and as a "
                "tool for building user interfaces\n",
                "end_date": "Unknown",
                "name": "swig",
                "profiles": {
                    "common": ["swig"],
                    "complete": ["swig", "swig-doc", "swig-gdb"],
                },
                "start_date": "Unknown",
                "stream": "4",
                "version": "8040020201001104431",
            },
            {
                "arch": "x86_64",
                "context": "fd72936b",
                "description": "Simplified Wrapper and Interface Generator "
                "(SWIG) is a software development tool for "
                "connecting C, C++ and Objective C programs with "
                "a variety of high-level programming languages. "
                "SWIG is primarily used with Perl, Python and "
                "Tcl/TK, but it has also been extended to Java, "
                "Eiffel and Guile. SWIG is normally used to "
                "create high-level interpreted programming "
                "environments, systems integration, and as a "
                "tool for building user interfaces\n",
                "end_date": date(2027, 5, 31),
                "name": "swig",
                "profiles": {
                    "common": ["swig"],
                    "complete": ["swig", "swig-doc", "swig-gdb"],
                },
                "start_date": date(2023, 5, 16),
                "stream": "4.1",
                "version": "8080020221213075530",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "pmdk",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "fd72936b",
                "description": "The Persistent Memory Development Kit is a "
                "collection of libraries for using memory-mapped "
                "persistence, optimized specifically for "
                "persistent memory.",
                "end_date": "Unknown",
                "name": "pmdk",
                "profiles": {},
                "start_date": "Unknown",
                "stream": "1_fileformat_v6",
                "version": "8080020221121213140",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "subversion",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "a51370e3",
                "description": "Apache Subversion, a Modern Version Control System",
                "end_date": "Unknown",
                "name": "subversion",
                "profiles": {
                    "common": ["subversion", "subversion-libs", "subversion-tools"],
                    "server": [
                        "mod_dav_svn",
                        "subversion",
                        "subversion-libs",
                        "subversion-tools",
                    ],
                },
                "start_date": "Unknown",
                "stream": "1.1",
                "version": "820181215112250",
            },
            {
                "arch": "x86_64",
                "context": "78111232",
                "description": "Apache Subversion, a Modern Version Control System",
                "end_date": date(2029, 5, 31),
                "name": "subversion",
                "profiles": {
                    "common": ["subversion", "subversion-libs", "subversion-tools"],
                    "server": [
                        "mod_dav_svn",
                        "subversion",
                        "subversion-libs",
                        "subversion-tools",
                    ],
                },
                "start_date": date(2019, 5, 7),
                "stream": "1.10",
                "version": "8070020220701055908",
            },
            {
                "arch": "x86_64",
                "context": "a74460ab",
                "description": "Apache Subversion, a Modern Version Control System",
                "end_date": date(2024, 5, 31),
                "name": "subversion",
                "profiles": {
                    "common": ["subversion", "subversion-libs", "subversion-tools"],
                    "server": [
                        "mod_dav_svn",
                        "subversion",
                        "subversion-libs",
                        "subversion-tools",
                    ],
                },
                "start_date": date(2021, 5, 18),
                "stream": "1.14",
                "version": "8070020220701055624",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "rust-toolset",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "b09eea91",
                "description": "Rust Toolset",
                "end_date": date(2019, 11, 30),
                "name": "rust-toolset",
                "profiles": {"common": ["rust-toolset"]},
                "start_date": date(2019, 5, 7),
                "stream": "rhel8",
                "version": "820181214214108",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "jaxb",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9d367344",
                "description": "Jakarta XML Binding defines an API and tools "
                "that automate the mapping between XML documents "
                "and Java objects. The Eclipse Implementation of "
                "JAXB project contains implementation of Jakarta "
                "XML Binding API.",
                "end_date": "Unknown",
                "name": "jaxb",
                "profiles": {"common": ["jaxb-runtime"]},
                "start_date": "Unknown",
                "stream": "4",
                "version": "8080020230207081414",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "python39",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "d47b87a4",
                "description": "This module gives users access to the internal "
                "Python 3.9 in RHEL8, as\n"
                "well as provides some additional Python "
                "packages the users might need.\n"
                "In addition to these you can install any "
                "python3-* package available\n"
                "in RHEL and use it with Python from this "
                "module.",
                "end_date": date(2025, 11, 30),
                "name": "python39",
                "profiles": {
                    "build": ["python39", "python39-devel", "python39-rpm-macros"],
                    "common": ["python39"],
                },
                "start_date": date(2021, 5, 18),
                "stream": "3.9",
                "version": "8100020240927003152",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "perl-DBD-SQLite",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "6bc6cad6",
                "description": "SQLite is a public domain RDBMS database engine "
                "that you can find at "
                "http://www.hwaci.com/sw/sqlite/. This Perl "
                "module provides a SQLite RDBMS module that uses "
                "the system SQLite libraries.\n",
                "end_date": "Unknown",
                "name": "perl-DBD-SQLite",
                "profiles": {"common": ["perl-DBD-SQLite"]},
                "start_date": "Unknown",
                "stream": "1.58",
                "version": "820181214121133",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "python27",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "43711c95",
                "description": "This module provides the Python 2.7 interpreter "
                "and additional Python\n"
                "packages the users might need.",
                "end_date": date(2024, 6, 30),
                "name": "python27",
                "profiles": {
                    "common": [
                        "python2",
                        "python2-libs",
                        "python2-pip",
                        "python2-setuptools",
                    ]
                },
                "start_date": date(2019, 5, 7),
                "stream": "2.7",
                "version": "820190212161047",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "postgresql",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "PostgreSQL is an advanced Object-Relational "
                "database management system (DBMS). The "
                "postgresql-server package contains the programs "
                "needed to create and run a PostgreSQL server, "
                "which will in turn allow you to create and "
                "maintain PostgreSQL databases. The base "
                "postgresql package contains the client programs "
                "that you'll need to access a PostgreSQL DBMS "
                "server.",
                "end_date": date(2024, 5, 31),
                "name": "postgresql",
                "profiles": {"client": ["postgresql"], "server": ["postgresql-server"]},
                "start_date": date(2019, 5, 7),
                "stream": "10",
                "version": "820190104140132",
            },
            {
                "arch": "x86_64",
                "context": "489197000000",
                "description": "PostgreSQL is an advanced Object-Relational "
                "database management system (DBMS). The "
                "postgresql-server package contains the programs "
                "needed to create and run a PostgreSQL server, "
                "which will in turn allow you to create and "
                "maintain PostgreSQL databases. The base "
                "postgresql package contains the client programs "
                "that you'll need to access a PostgreSQL DBMS "
                "server.",
                "end_date": date(2029, 5, 31),
                "name": "postgresql",
                "profiles": {"client": ["postgresql"], "server": ["postgresql-server"]},
                "start_date": date(2019, 11, 5),
                "stream": "12",
                "version": "8100020241122084405",
            },
            {
                "arch": "x86_64",
                "context": "489197000000",
                "description": "PostgreSQL is an advanced Object-Relational "
                "database management system (DBMS). The "
                "postgresql-server package contains the programs "
                "needed to create and run a PostgreSQL server, "
                "which will in turn allow you to create and "
                "maintain PostgreSQL databases. The base "
                "postgresql package contains the client programs "
                "that you'll need to access a PostgreSQL DBMS "
                "server.",
                "end_date": date(2026, 5, 31),
                "name": "postgresql",
                "profiles": {"client": ["postgresql"], "server": ["postgresql-server"]},
                "start_date": date(2021, 5, 18),
                "stream": "13",
                "version": "8100020241122084628",
            },
            {
                "arch": "x86_64",
                "context": "489197000000",
                "description": "PostgreSQL is an advanced Object-Relational "
                "database management system (DBMS). The "
                "postgresql-server package contains the programs "
                "needed to create and run a PostgreSQL server, "
                "which will in turn allow you to create and "
                "maintain PostgreSQL databases. The base "
                "postgresql package contains the client programs "
                "that you'll need to access a PostgreSQL DBMS "
                "server.",
                "end_date": date(2028, 5, 31),
                "name": "postgresql",
                "profiles": {"client": ["postgresql"], "server": ["postgresql-server"]},
                "start_date": date(2023, 5, 16),
                "stream": "15",
                "version": "8100020241122084744",
            },
            {
                "arch": "x86_64",
                "context": "489197000000",
                "description": "PostgreSQL is an advanced Object-Relational "
                "database management system (DBMS). The "
                "postgresql-server package contains the programs "
                "needed to create and run a PostgreSQL server, "
                "which will in turn allow you to create and "
                "maintain PostgreSQL databases. The base "
                "postgresql package contains the client programs "
                "that you'll need to access a PostgreSQL DBMS "
                "server.",
                "end_date": date(2029, 5, 31),
                "name": "postgresql",
                "profiles": {"client": ["postgresql"], "server": ["postgresql-server"]},
                "start_date": date(2024, 5, 22),
                "stream": "16",
                "version": "8100020241122085009",
            },
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "PostgreSQL is an advanced Object-Relational "
                "database management system (DBMS). The "
                "postgresql-server package contains the programs "
                "needed to create and run a PostgreSQL server, "
                "which will in turn allow you to create and "
                "maintain PostgreSQL databases. The base "
                "postgresql package contains the client programs "
                "that you'll need to access a PostgreSQL DBMS "
                "server.",
                "end_date": date(2021, 11, 30),
                "name": "postgresql",
                "profiles": {"client": ["postgresql"], "server": ["postgresql-server"]},
                "start_date": date(2019, 5, 7),
                "stream": "9.6",
                "version": "820190104140337",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "varnish",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "Varnish Cache web application accelerator",
                "end_date": date(2029, 5, 31),
                "name": "varnish",
                "profiles": {"common": ["varnish", "varnish-modules"]},
                "start_date": date(2019, 5, 7),
                "stream": "6",
                "version": "820181213144015",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "mysql",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "MySQL is a multi-user, multi-threaded SQL "
                "database server. MySQL is a client/server "
                "implementation consisting of a server daemon "
                "(mysqld) and many different client programs and "
                "libraries. The base package contains the "
                "standard MySQL client programs and generic "
                "MySQL files.",
                "end_date": "Unknown",
                "name": "mysql",
                "profiles": {"client": ["mysql"], "server": ["mysql-server"]},
                "start_date": "Unknown",
                "stream": "8",
                "version": "820190104140943",
            },
            {
                "arch": "x86_64",
                "context": "a75119d5",
                "description": "MySQL is a multi-user, multi-threaded SQL "
                "database server. MySQL is a client/server "
                "implementation consisting of a server daemon "
                "(mysqld) and many different client programs and "
                "libraries. The base package contains the "
                "standard MySQL client programs and generic "
                "MySQL files.",
                "end_date": date(2026, 4, 30),
                "name": "mysql",
                "profiles": {"client": ["mysql"], "server": ["mysql-server"]},
                "start_date": date(2019, 5, 7),
                "stream": "8.0",
                "version": "8090020240126173013",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "nginx",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "nginx 1.14 webserver module",
                "end_date": date(2021, 5, 31),
                "name": "nginx",
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
                "start_date": date(2019, 5, 7),
                "stream": "1.14",
                "version": "820181214004940",
            },
            {
                "arch": "x86_64",
                "context": "522a0ee4",
                "description": "nginx 1.16 webserver module",
                "end_date": date(2021, 10, 30),
                "name": "nginx",
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
                "start_date": date(2019, 11, 5),
                "stream": "1.16",
                "version": "8040020210526102347",
            },
            {
                "arch": "x86_64",
                "context": "522a0ee4",
                "description": "nginx 1.18 webserver module",
                "end_date": date(2022, 11, 30),
                "name": "nginx",
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
                "start_date": date(2020, 11, 3),
                "stream": "1.18",
                "version": "8040020210526100943",
            },
            {
                "arch": "x86_64",
                "context": "63b34585",
                "description": "nginx 1.20 webserver module",
                "end_date": date(2023, 11, 30),
                "name": "nginx",
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
                "start_date": date(2021, 11, 9),
                "stream": "1.20",
                "version": "8080020231012034601",
            },
            {
                "arch": "x86_64",
                "context": "63b34585",
                "description": "nginx 1.22 webserver module",
                "end_date": date(2025, 11, 30),
                "name": "nginx",
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
                "start_date": date(2023, 5, 16),
                "stream": "1.22",
                "version": "8080020231011224613",
            },
            {
                "arch": "x86_64",
                "context": "e155f54d",
                "description": "nginx 1.24 webserver module",
                "end_date": date(2029, 5, 31),
                "name": "nginx",
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
                "start_date": date(2024, 5, 22),
                "stream": "1.24",
                "version": "8100020240119085512",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "rhn-tools",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "e122ddfa",
                "description": "Red Hat Satellite 5 tools packages providing "
                "additional functionality like e.g. provisioning "
                "or configuration management.",
                "end_date": "Unknown",
                "name": "rhn-tools",
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
                "start_date": "Unknown",
                "stream": "1",
                "version": "820190321094720",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "perl-DBI",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "2fbcbb20",
                "description": "DBI is a database access Application "
                "Programming Interface (API) for the Perl "
                "language. The DBI API specification defines a "
                "set of functions, variables and conventions "
                "that provide a consistent database interface "
                "independent of the actual database being "
                "used.\n",
                "end_date": "Unknown",
                "name": "perl-DBI",
                "profiles": {"common": ["perl-DBI"]},
                "start_date": "Unknown",
                "stream": "1.641",
                "version": "820190116185335",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "pki-core",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "5a87be8a",
                "description": "A module for PKI Core packages.",
                "end_date": date(2019, 11, 30),
                "name": "pki-core",
                "profiles": {},
                "start_date": date(2019, 5, 7),
                "stream": "10.6",
                "version": "820190128182152",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "llvm-toolset",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "LLVM Tools and libraries",
                "end_date": date(2019, 11, 30),
                "name": "llvm-toolset",
                "profiles": {"common": ["llvm-toolset"]},
                "start_date": date(2019, 5, 7),
                "stream": "rhel8",
                "version": "820190207221833",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "log4j",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9d367344",
                "description": "Log4j is a popular Java logging library that "
                "allows the programmer to output log statements "
                "to a variety of output targets.",
                "end_date": "Unknown",
                "name": "log4j",
                "profiles": {"common": ["log4j"]},
                "start_date": "Unknown",
                "stream": "2",
                "version": "8080020221020123337",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "perl-FCGI",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "2fbcbb20",
                "description": "This allows you to write a FastCGI client in the Perl language.\n",
                "end_date": "Unknown",
                "name": "perl-FCGI",
                "profiles": {"common": ["perl-FCGI"]},
                "start_date": "Unknown",
                "stream": "0.78",
                "version": "820181214153815",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "perl-IO-Socket-SSL",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "03d935ed",
                "description": "IO::Socket::SSL is a drop-in replacement for "
                "IO::Socket::IP that uses TLS to encrypt data "
                "before it is transferred to a remote server or "
                "client. IO::Socket::SSL supports all the extra "
                "features that one needs to write a "
                "full-featured TLS client or server application "
                "like multiple TLS contexts, cipher selection, "
                "certificate verification, and TLS version "
                "selection. Net::SSLeay offers some high level "
                "convenience functions for accessing web pages "
                "on TLS servers, a sslcat() function for writing "
                "your own clients, and finally access to the API "
                "of OpenSSL library so you can write servers or "
                "clients for more complicated applications.\n",
                "end_date": "Unknown",
                "name": "perl-IO-Socket-SSL",
                "profiles": {"common": ["perl-IO-Socket-SSL", "perl-Net-SSLeay"]},
                "start_date": "Unknown",
                "stream": "2.066",
                "version": "8060020211122104554",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "python38",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "d9f72c26",
                "description": "This module gives users access to the internal "
                "Python 3.8 in RHEL8, as\n"
                "well as provides some additional Python "
                "packages the users might need.\n"
                "In addition to these you can install any "
                "python3-* package available\n"
                "in RHEL and use it with Python from this "
                "module.",
                "end_date": date(2023, 5, 31),
                "name": "python38",
                "profiles": {
                    "build": ["python38", "python38-devel", "python38-rpm-macros"],
                    "common": ["python38"],
                },
                "start_date": date(2020, 4, 28),
                "stream": "3.8",
                "version": "8090020230810143931",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "eclipse",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "498c0fee",
                "description": "The Eclipse platform is designed for building "
                "integrated development environments (IDEs), "
                "desktop applications, and everything in "
                "between.",
                "end_date": date(2021, 8, 20),
                "name": "eclipse",
                "profiles": {
                    "java": [
                        "eclipse-equinox-osgi",
                        "eclipse-jdt",
                        "eclipse-pde",
                        "eclipse-platform",
                        "eclipse-swt",
                    ]
                },
                "start_date": date(2020, 4, 28),
                "stream": "rhel8",
                "version": "8030020201023061315",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "idm",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "49cc9d1b",
                "description": "RHEL IdM is an integrated solution to provide "
                "centrally managed Identity (users, hosts, "
                "services), Authentication (SSO, 2FA), and "
                "Authorization (host access control, SELinux "
                "user roles, services). The solution provides "
                "features for further integration with Linux "
                "based clients (SUDO, automount) and integration "
                "with Active Directory based infrastructures "
                "(Trusts).\n"
                "This module stream supports only client side of "
                "RHEL IdM solution",
                "end_date": date(2029, 5, 31),
                "name": "idm",
                "profiles": {"common": ["ipa-client"]},
                "start_date": date(2019, 5, 7),
                "stream": "client",
                "version": "820190227213458",
            },
            {
                "arch": "x86_64",
                "context": "5986f621",
                "description": "RHEL IdM is an integrated solution to provide "
                "centrally managed Identity (users, hosts, "
                "services), Authentication (SSO, 2FA), and "
                "Authorization (host access control, SELinux "
                "user roles, services). The solution provides "
                "features for further integration with Linux "
                "based clients (SUDO, automount) and integration "
                "with Active Directory based infrastructures "
                "(Trusts).",
                "end_date": date(2029, 5, 31),
                "name": "idm",
                "profiles": {
                    "adtrust": [
                        "ipa-idoverride-memberof-plugin",
                        "ipa-server-trust-ad",
                    ],
                    "client": ["ipa-client"],
                    "common": ["ipa-client"],
                    "dns": ["ipa-server", "ipa-server-dns"],
                    "server": ["ipa-server"],
                },
                "start_date": date(2019, 5, 7),
                "stream": "DL1",
                "version": "820190227212412",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "python36",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "17efdbc7",
                "description": "This module gives users access to the internal "
                "Python 3.6 in RHEL8, as\n"
                "well as provides some additional Python "
                "packages the users might need.\n"
                "In addition to these you can install any "
                "python3-* package available\n"
                "in RHEL and use it with Python from this "
                "module.",
                "end_date": date(2029, 5, 31),
                "name": "python36",
                "profiles": {
                    "build": ["python36", "python36-devel", "python36-rpm-macros"],
                    "common": ["python36"],
                },
                "start_date": date(2019, 5, 7),
                "stream": "3.6",
                "version": "820190123171828",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "httpd",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "Apache httpd is a powerful, efficient, and extensible HTTP server.",
                "end_date": date(2029, 5, 31),
                "name": "httpd",
                "profiles": {
                    "common": [
                        "httpd",
                        "httpd-filesystem",
                        "httpd-tools",
                        "mod_http2",
                        "mod_ssl",
                    ],
                    "devel": [
                        "httpd",
                        "httpd-devel",
                        "httpd-filesystem",
                        "httpd-tools",
                    ],
                    "minimal": ["httpd"],
                },
                "start_date": date(2019, 5, 7),
                "stream": "2.4",
                "version": "820190206142837",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "perl-libwww-perl",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "b947e2fe",
                "description": "The libwww-perl collection is a set of Perl "
                "modules which provide a simple and consistent "
                "application programming interface to the "
                "World-Wide Web. The main focus of the library "
                "is to provide classes and functions that enable "
                "you to write WWW clients. The library also "
                "contains modules that are of more general use "
                "and even classes that help you implement simple "
                "HTTP servers. LWP::Protocol::https adds a "
                "support for an HTTPS protocol.\n",
                "end_date": "Unknown",
                "name": "perl-libwww-perl",
                "profiles": {"common": ["perl-LWP-Protocol-https", "perl-libwww-perl"]},
                "start_date": "Unknown",
                "stream": "6.34",
                "version": "8060020210901111951",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "jmc",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "6392b1f8",
                "description": "Java Mission Control is a powerful profiler for "
                "HotSpot JVMs and has an advanced set of tools "
                "that enables efficient and detailed analysis of "
                "the extensive data collected by Java Flight "
                "Recorder. The tool chain enables developers and "
                "administrators to collect and analyze data from "
                "Java applications running locally or deployed "
                "in production environments.",
                "end_date": date(2020, 5, 31),
                "name": "jmc",
                "profiles": {"common": ["jmc"], "core": ["jmc-core"]},
                "start_date": date(2019, 11, 5),
                "stream": "rhel8",
                "version": "8050020211005144542",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "mailman",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "77fc8825",
                "description": "An initial version of the mailman mailing list management software",
                "end_date": date(2024, 6, 30),
                "name": "mailman",
                "profiles": {"common": ["mailman"]},
                "start_date": date(2019, 5, 7),
                "stream": "2.1",
                "version": "820181213140247",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "perl-DBD-MySQL",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "6bc6cad6",
                "description": "DBD::mysql is the Perl5 Database Interface "
                "driver for the MySQL database. In other words: "
                "DBD::mysql is an interface between the Perl "
                "programming language and the MySQL programming "
                "API that comes with the MySQL relational "
                "database management system.\n",
                "end_date": "Unknown",
                "name": "perl-DBD-MySQL",
                "profiles": {"common": ["perl-DBD-MySQL"]},
                "start_date": "Unknown",
                "stream": "4.046",
                "version": "820181214121012",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "redis",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "redis 5 module",
                "end_date": date(2022, 5, 31),
                "name": "redis",
                "profiles": {"common": ["redis"]},
                "start_date": date(2019, 5, 7),
                "stream": "5",
                "version": "820181217094919",
            },
            {
                "arch": "x86_64",
                "context": "3b9f49c4",
                "description": "redis 6 module",
                "end_date": date(2029, 5, 31),
                "name": "redis",
                "profiles": {"common": ["redis"]},
                "start_date": date(2021, 5, 18),
                "stream": "6",
                "version": "8070020220509142426",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "389-ds",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "1fc8b219",
                "description": "389 Directory Server is an LDAPv3 compliant "
                "server.  The base package includes the LDAP "
                "server and command line utilities for server "
                "administration.",
                "end_date": date(2019, 11, 30),
                "name": "389-ds",
                "profiles": {},
                "start_date": date(2019, 5, 7),
                "stream": "1.4",
                "version": "820190201170147",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "ant",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "5ea3b708",
                "description": "Apache Ant is a Java library and command-line "
                "tool whose mission is to drive processes "
                "described in build files as targets and "
                "extension points dependent upon each other. The "
                "main known usage of Ant is the build of Java "
                "applications. Ant supplies a number of built-in "
                "tasks allowing to compile, assemble, test and "
                "run Java applications. Ant can also be used "
                "effectively to build non Java applications, for "
                "instance C or C++ applications. More generally, "
                "Ant can be used to pilot any type of process "
                "which can be described in terms of targets and "
                "tasks.",
                "end_date": "Unknown",
                "name": "ant",
                "profiles": {"common": ["ant"]},
                "start_date": "Unknown",
                "stream": "1.1",
                "version": "820181213135032",
            },
            {
                "arch": "x86_64",
                "context": "417e5c08",
                "description": "Apache Ant is a Java library and command-line "
                "tool whose mission is to drive processes "
                "described in build files as targets and "
                "extension points dependent upon each other. The "
                "main known usage of Ant is the build of Java "
                "applications. Ant supplies a number of built-in "
                "tasks allowing to compile, assemble, test and "
                "run Java applications. Ant can also be used "
                "effectively to build non Java applications, for "
                "instance C or C++ applications. More generally, "
                "Ant can be used to pilot any type of process "
                "which can be described in terms of targets and "
                "tasks.",
                "end_date": date(2029, 5, 31),
                "name": "ant",
                "profiles": {"common": ["ant"]},
                "start_date": date(2019, 5, 7),
                "stream": "1.10",
                "version": "8100020240221104459",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "mod_auth_openidc",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "This module enables an Apache 2.x web server to "
                "operate as an OpenID Connect Relying Party "
                "and/or OAuth 2.0 Resource Server.",
                "end_date": date(2029, 5, 31),
                "name": "mod_auth_openidc",
                "profiles": {},
                "start_date": date(2019, 5, 7),
                "stream": "2.3",
                "version": "820181213140451",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "nodejs",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "Node.js is a platform built on Chrome's "
                "JavaScript runtime for easily building fast, "
                "scalable network applications. Node.js uses an "
                "event-driven, non-blocking I/O model that makes "
                "it lightweight and efficient, perfect for "
                "data-intensive real-time applications that run "
                "across distributed devices.",
                "end_date": date(2021, 4, 30),
                "name": "nodejs",
                "profiles": {
                    "common": ["nodejs", "npm"],
                    "development": ["nodejs", "nodejs-devel", "npm"],
                    "minimal": ["nodejs"],
                    "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                },
                "start_date": date(2019, 5, 7),
                "stream": "10",
                "version": "820190108092226",
            },
            {
                "arch": "x86_64",
                "context": "ad008a3a",
                "description": "Node.js is a platform built on Chrome's "
                "JavaScript runtime for easily building fast, "
                "scalable network applications. Node.js uses an "
                "event-driven, non-blocking I/O model that makes "
                "it lightweight and efficient, perfect for "
                "data-intensive real-time applications that run "
                "across distributed devices.",
                "end_date": date(2022, 4, 30),
                "name": "nodejs",
                "profiles": {
                    "common": ["nodejs", "npm"],
                    "development": ["nodejs", "nodejs-devel", "npm"],
                    "minimal": ["nodejs"],
                    "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                },
                "start_date": date(2019, 11, 5),
                "stream": "12",
                "version": "8060020220523160029",
            },
            {
                "arch": "x86_64",
                "context": "bd1311ed",
                "description": "Node.js is a platform built on Chrome's "
                "JavaScript runtime for easily building fast, "
                "scalable network applications. Node.js uses an "
                "event-driven, non-blocking I/O model that makes "
                "it lightweight and efficient, perfect for "
                "data-intensive real-time applications that run "
                "across distributed devices.",
                "end_date": date(2023, 4, 30),
                "name": "nodejs",
                "profiles": {
                    "common": ["nodejs", "npm"],
                    "development": ["nodejs", "nodejs-devel", "npm"],
                    "minimal": ["nodejs"],
                    "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                },
                "start_date": date(2020, 11, 3),
                "stream": "14",
                "version": "8070020230306170042",
            },
            {
                "arch": "x86_64",
                "context": "a75119d5",
                "description": "Node.js is a platform built on Chrome's "
                "JavaScript runtime for easily building fast, "
                "scalable network applications. Node.js uses an "
                "event-driven, non-blocking I/O model that makes "
                "it lightweight and efficient, perfect for "
                "data-intensive real-time applications that run "
                "across distributed devices.",
                "end_date": date(2024, 4, 30),
                "name": "nodejs",
                "profiles": {
                    "common": ["nodejs", "npm"],
                    "development": ["nodejs", "nodejs-devel", "npm"],
                    "minimal": ["nodejs"],
                    "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                },
                "start_date": date(2021, 11, 9),
                "stream": "16",
                "version": "8090020240315081818",
            },
            {
                "arch": "x86_64",
                "context": "489197000000",
                "description": "Node.js is a platform built on Chrome's "
                "JavaScript runtime for easily building fast, "
                "scalable network applications. Node.js uses an "
                "event-driven, non-blocking I/O model that makes "
                "it lightweight and efficient, perfect for "
                "data-intensive real-time applications that run "
                "across distributed devices.",
                "end_date": date(2025, 4, 30),
                "name": "nodejs",
                "profiles": {
                    "common": ["nodejs", "npm"],
                    "development": ["nodejs", "nodejs-devel", "npm"],
                    "minimal": ["nodejs"],
                    "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                },
                "start_date": date(2022, 11, 9),
                "stream": "18",
                "version": "8100020240807161023",
            },
            {
                "arch": "x86_64",
                "context": "489197000000",
                "description": "Node.js is a platform built on Chrome's "
                "JavaScript runtime for easily building fast, "
                "scalable network applications. Node.js uses an "
                "event-driven, non-blocking I/O model that makes "
                "it lightweight and efficient, perfect for "
                "data-intensive real-time applications that run "
                "across distributed devices.",
                "end_date": date(2026, 4, 30),
                "name": "nodejs",
                "profiles": {
                    "common": ["nodejs", "npm"],
                    "development": ["nodejs", "nodejs-devel", "npm"],
                    "minimal": ["nodejs"],
                    "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                },
                "start_date": date(2023, 11, 14),
                "stream": "20",
                "version": "8100020240808073736",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "php",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "765540",
                "description": "php 7.2 module",
                "end_date": date(2021, 5, 31),
                "name": "php",
                "profiles": {
                    "common": [
                        "php-cli",
                        "php-common",
                        "php-fpm",
                        "php-json",
                        "php-mbstring",
                        "php-xml",
                    ],
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
                "start_date": date(2019, 5, 7),
                "stream": "7.2",
                "version": "820181215112050",
            },
            {
                "arch": "x86_64",
                "context": "ceb1cf90",
                "description": "php 7.3 module",
                "end_date": date(2021, 11, 30),
                "name": "php",
                "profiles": {
                    "common": [
                        "php-cli",
                        "php-common",
                        "php-fpm",
                        "php-json",
                        "php-mbstring",
                        "php-xml",
                    ],
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
                "start_date": date(2019, 11, 5),
                "stream": "7.3",
                "version": "8020020200715124551",
            },
            {
                "arch": "x86_64",
                "context": "f7998665",
                "description": "php 7.4 module",
                "end_date": date(2029, 5, 31),
                "name": "php",
                "profiles": {
                    "common": [
                        "php-cli",
                        "php-common",
                        "php-fpm",
                        "php-json",
                        "php-mbstring",
                        "php-xml",
                    ],
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
                "start_date": date(2020, 11, 3),
                "stream": "7.4",
                "version": "8100020241113075828",
            },
            {
                "arch": "x86_64",
                "context": "0b4eb31d",
                "description": "php 8.0 module",
                "end_date": date(2024, 11, 30),
                "name": "php",
                "profiles": {
                    "common": [
                        "php-cli",
                        "php-common",
                        "php-fpm",
                        "php-mbstring",
                        "php-xml",
                    ],
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
                "start_date": date(2022, 5, 10),
                "stream": "8.0",
                "version": "8080020231006102311",
            },
            {
                "arch": "x86_64",
                "context": "f7998665",
                "description": "php 8.2 module",
                "end_date": date(2029, 5, 31),
                "name": "php",
                "profiles": {
                    "common": [
                        "php-cli",
                        "php-common",
                        "php-fpm",
                        "php-mbstring",
                        "php-xml",
                    ],
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
                "start_date": date(2024, 5, 22),
                "stream": "8.2",
                "version": "8100020241112130045",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "ruby",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "Ruby is the interpreted scripting language for "
                "quick and easy object-oriented programming.  It "
                "has many features to process text files and to "
                "do system management tasks (as in Perl).  It is "
                "simple, straight-forward, and extensible.",
                "end_date": date(2029, 5, 31),
                "name": "ruby",
                "profiles": {"common": ["ruby"]},
                "start_date": date(2019, 5, 7),
                "stream": "2.5",
                "version": "820190111110530",
            },
            {
                "arch": "x86_64",
                "context": "ad008a3a",
                "description": "Ruby is the interpreted scripting language for "
                "quick and easy object-oriented programming.  It "
                "has many features to process text files and to "
                "do system management tasks (as in Perl).  It is "
                "simple, straight-forward, and extensible.",
                "end_date": date(2022, 3, 31),
                "name": "ruby",
                "profiles": {"common": ["ruby"]},
                "start_date": date(2019, 11, 5),
                "stream": "2.6",
                "version": "8060020220527104428",
            },
            {
                "arch": "x86_64",
                "context": "63b34585",
                "description": "Ruby is the interpreted scripting language for "
                "quick and easy object-oriented programming.  It "
                "has many features to process text files and to "
                "do system management tasks (as in Perl).  It is "
                "simple, straight-forward, and extensible.",
                "end_date": date(2023, 3, 31),
                "name": "ruby",
                "profiles": {"common": ["ruby"]},
                "start_date": date(2020, 11, 3),
                "stream": "2.7",
                "version": "8080020230427102918",
            },
            {
                "arch": "x86_64",
                "context": "489197000000",
                "description": "Ruby is the interpreted scripting language for "
                "quick and easy object-oriented programming.  It "
                "has many features to process text files and to "
                "do system management tasks (as in Perl).  It is "
                "simple, straight-forward, and extensible.",
                "end_date": date(2024, 3, 31),
                "name": "ruby",
                "profiles": {"common": ["ruby"]},
                "start_date": date(2021, 11, 9),
                "stream": "3.0",
                "version": "8100020240522072634",
            },
            {
                "arch": "x86_64",
                "context": "489197000000",
                "description": "Ruby is the interpreted scripting language for "
                "quick and easy object-oriented programming.  It "
                "has many features to process text files and to "
                "do system management tasks (as in Perl).  It is "
                "simple, straight-forward, and extensible.",
                "end_date": date(2025, 3, 31),
                "name": "ruby",
                "profiles": {"common": ["ruby"]},
                "start_date": date(2022, 11, 9),
                "stream": "3.1",
                "version": "8100020241127152928",
            },
            {
                "arch": "x86_64",
                "context": "489197000000",
                "description": "Ruby is the interpreted scripting language for "
                "quick and easy object-oriented programming.  It "
                "has many features to process text files and to "
                "do system management tasks (as in Perl).  It is "
                "simple, straight-forward, and extensible.",
                "end_date": date(2027, 3, 31),
                "name": "ruby",
                "profiles": {"common": ["ruby"]},
                "start_date": date(2024, 5, 22),
                "stream": "3.3",
                "version": "8100020240906074654",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "gimp",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "77fc8825",
                "description": "GIMP (GNU Image Manipulation Program) is a "
                "powerful image composition and\n"
                "editing program, which can be extremely useful "
                "for creating logos and other\n"
                "graphics for webpages. ",
                "end_date": "Unknown",
                "name": "gimp",
                "profiles": {
                    "common": ["gimp"],
                    "devel": ["gimp-devel", "gimp-devel-tools"],
                },
                "start_date": "Unknown",
                "stream": "2.8",
                "version": "820181213135540",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "mariadb",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "e155f54d",
                "description": "MariaDB is a community developed branch of "
                "MySQL. MariaDB is a multi-user, multi-threaded "
                "SQL database server. It is a client/server "
                "implementation consisting of a server daemon "
                "(mysqld) and many different client programs and "
                "libraries. The base package contains the "
                "standard MariaDB/MySQL client programs and "
                "generic MySQL files.",
                "end_date": date(2028, 5, 31),
                "name": "mariadb",
                "profiles": {
                    "client": ["mariadb"],
                    "galera": ["mariadb-server", "mariadb-server-galera"],
                    "server": ["mariadb-server"],
                },
                "start_date": date(2024, 5, 22),
                "stream": "10.11",
                "version": "8100020240129174731",
            },
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "MariaDB is a community developed branch of "
                "MySQL. MariaDB is a multi-user, multi-threaded "
                "SQL database server. It is a client/server "
                "implementation consisting of a server daemon "
                "(mysqld) and many different client programs and "
                "libraries. The base package contains the "
                "standard MariaDB/MySQL client programs and "
                "generic MySQL files.",
                "end_date": date(2029, 5, 31),
                "name": "mariadb",
                "profiles": {
                    "client": ["mariadb"],
                    "galera": ["mariadb-server", "mariadb-server-galera"],
                    "server": ["mariadb-server"],
                },
                "start_date": date(2019, 5, 7),
                "stream": "10.3",
                "version": "820190314153642",
            },
            {
                "arch": "x86_64",
                "context": "63b34585",
                "description": "MariaDB is a community developed branch of "
                "MySQL. MariaDB is a multi-user, multi-threaded "
                "SQL database server. It is a client/server "
                "implementation consisting of a server daemon "
                "(mysqld) and many different client programs and "
                "libraries. The base package contains the "
                "standard MariaDB/MySQL client programs and "
                "generic MySQL files.",
                "end_date": date(2026, 5, 31),
                "name": "mariadb",
                "profiles": {
                    "client": ["mariadb"],
                    "galera": ["mariadb-server", "mariadb-server-galera"],
                    "server": ["mariadb-server"],
                },
                "start_date": date(2021, 5, 18),
                "stream": "10.5",
                "version": "8080020231003163755",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "scala",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "2b79a98f",
                "description": "Scala is a general purpose programming language "
                "designed to express common programming patterns "
                "in a concise, elegant, and type-safe way. It "
                "smoothly integrates features of object-oriented "
                "and functional languages. It is also fully "
                "interoperable with Java.",
                "end_date": "Unknown",
                "name": "scala",
                "profiles": {"common": ["scala"]},
                "start_date": "Unknown",
                "stream": "2.1",
                "version": "820181213143541",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "perl-YAML",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "8652dbeb",
                "description": "The YAML.pm module implements a YAML Loader and "
                "Dumper based on the YAML 1.0 specification. "
                "YAML is a generic data serialization language "
                "that is optimized for human readability. It can "
                "be used to express the data structures of most "
                "modern programming languages, including Perl. "
                "For information on the YAML syntax, please "
                "refer to the YAML specification.\n",
                "end_date": "Unknown",
                "name": "perl-YAML",
                "profiles": {"common": ["perl-YAML"]},
                "start_date": "Unknown",
                "stream": "1.24",
                "version": "820181214175558",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "javapackages-runtime",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "302ab70f",
                "description": "This module contains basic filesystem layout "
                "and runtime utilities used to support system "
                "applications written in JVM languages.",
                "end_date": "Unknown",
                "name": "javapackages-runtime",
                "profiles": {"common": ["javapackages-filesystem", "javapackages-tools"]},
                "start_date": "Unknown",
                "stream": "201801",
                "version": "820181213140046",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "perl",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "ee766497",
                "description": "Perl is a high-level programming language with "
                "roots in C, sed, awk and shell scripting. Perl "
                "is good at handling processes and files, and is "
                "especially good at handling text. Perl's "
                "hallmarks are practicality and efficiency. "
                "While it is used to do a lot of different "
                "things, Perl's most common applications are "
                "system administration utilities and web "
                "programming.\n",
                "end_date": date(2021, 5, 31),
                "name": "perl",
                "profiles": {"common": ["perl-core"], "minimal": ["perl"]},
                "start_date": date(2019, 5, 7),
                "stream": "5.24",
                "version": "820190207164249",
            },
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "Perl is a high-level programming language with "
                "roots in C, sed, awk and shell scripting. Perl "
                "is good at handling processes and files, and is "
                "especially good at handling text. Perl's "
                "hallmarks are practicality and efficiency. "
                "While it is used to do a lot of different "
                "things, Perl's most common applications are "
                "system administration utilities and web "
                "programming.\n",
                "end_date": date(2029, 5, 31),
                "name": "perl",
                "profiles": {"common": ["perl"], "minimal": ["perl-interpreter"]},
                "start_date": date(2019, 5, 7),
                "stream": "5.26",
                "version": "820181219174508",
            },
            {
                "arch": "x86_64",
                "context": "466ea64f",
                "description": "Perl is a high-level programming language with "
                "roots in C, sed, awk and shell scripting. Perl "
                "is good at handling processes and files, and is "
                "especially good at handling text. Perl's "
                "hallmarks are practicality and efficiency. "
                "While it is used to do a lot of different "
                "things, Perl's most common applications are "
                "system administration utilities and web "
                "programming.\n",
                "end_date": "Unknown",
                "name": "perl",
                "profiles": {"common": ["perl"], "minimal": ["perl-interpreter"]},
                "start_date": "Unknown",
                "stream": "5.3",
                "version": "8040020200923213406",
            },
            {
                "arch": "x86_64",
                "context": "9fe1d287",
                "description": "Perl is a high-level programming language with "
                "roots in C, sed, awk and shell scripting. Perl "
                "is good at handling processes and files, and is "
                "especially good at handling text. Perl's "
                "hallmarks are practicality and efficiency. "
                "While it is used to do a lot of different "
                "things, Perl's most common applications are "
                "system administration utilities and web "
                "programming.\n",
                "end_date": date(2025, 4, 30),
                "name": "perl",
                "profiles": {"common": ["perl"], "minimal": ["perl-interpreter"]},
                "start_date": date(2022, 5, 10),
                "stream": "5.32",
                "version": "8100020240314121426",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "inkscape",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "77fc8825",
                "description": "Inkscape is a vector graphics editor, with "
                "capabilities similar to\n"
                "Illustrator, CorelDraw, or Xara X, using the "
                "W3C standard Scalable Vector\n"
                "Graphics (SVG) file format.  It is therefore a "
                "very useful tool for web\n"
                "designers and as an interchange format for "
                "desktop publishing.\n"
                "\n"
                "Inkscape supports many advanced SVG features "
                "(markers, clones, alpha\n"
                "blending, etc.) and great care is taken in "
                "designing a streamlined\n"
                "interface. It is very easy to edit nodes, "
                "perform complex path operations,\n"
                "trace bitmaps and much more.",
                "end_date": "Unknown",
                "name": "inkscape",
                "profiles": {"common": ["inkscape"]},
                "start_date": "Unknown",
                "stream": "0.92.3",
                "version": "820181213140018",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "mercurial",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "77fc8825",
                "description": "Mercurial is a fast, lightweight source control "
                "management system designed for efficient "
                "handling of very large distributed projects.",
                "end_date": date(2022, 11, 30),
                "name": "mercurial",
                "profiles": {"common": ["mercurial"]},
                "start_date": date(2019, 5, 7),
                "stream": "4.8",
                "version": "820190108205035",
            },
            {
                "arch": "x86_64",
                "context": "3dbb8329",
                "description": "Mercurial is a fast, lightweight source control "
                "management system designed for efficient "
                "handling of very large distributed projects.",
                "end_date": date(2025, 11, 30),
                "name": "mercurial",
                "profiles": {"common": ["mercurial"]},
                "start_date": date(2022, 11, 9),
                "stream": "6.2",
                "version": "8070020220729131051",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "perl-App-cpanminus",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "e5ce1481",
                "description": "This is a CPAN client that requires zero "
                "configuration, and stands alone but it's "
                "maintainable and extensible with plug-ins and "
                "friendly to shell scripting.\n",
                "end_date": "Unknown",
                "name": "perl-App-cpanminus",
                "profiles": {"common": ["perl-App-cpanminus"]},
                "start_date": "Unknown",
                "stream": "1.7044",
                "version": "820181214184336",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "container-tools",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "20125149",
                "description": "Contains SELinux policies, binaries and other "
                "dependencies for use with container runtimes",
                "end_date": "Unknown",
                "name": "container-tools",
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
                "start_date": "Unknown",
                "stream": "1",
                "version": "820190220135513",
            },
            {
                "arch": "x86_64",
                "context": "830d479e",
                "description": "Stable versions of podman 1.6, buildah 1.11, "
                "skopeo 0.1, runc, conmon, CRIU, Udica, etc as "
                "well as dependencies such as container-selinux "
                "built and tested together. Released with RHEL "
                "8.2 and supported for 24 months. During the "
                "support lifecycle, back ports of important, "
                "critical vulnerabilities (CVEs, RHSAs) and bug "
                "fixes (RHBAs) are provided to this stream, and "
                "versions do not move forward. For more "
                "information see: "
                "https://access.redhat.com/support/policy/updates/containertools",
                "end_date": "Unknown",
                "name": "container-tools",
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
                "start_date": "Unknown",
                "stream": "2",
                "version": "8030020210302075156",
            },
            {
                "arch": "x86_64",
                "context": "e34216c9",
                "description": "Stable versions of podman 1.6, buildah 1.11, "
                "skopeo 0.1, runc, conmon, CRIU, Udica, etc as "
                "well as dependencies such as container-selinux "
                "built and tested together. Released with RHEL "
                "8.2 and supported for 24 months. During the "
                "support lifecycle, back ports of important, "
                "critical vulnerabilities (CVEs, RHSAs) and bug "
                "fixes (RHBAs) are provided to this stream, and "
                "versions do not move forward. For more "
                "information see: "
                "https://access.redhat.com/support/policy/updates/containertools",
                "end_date": date(2022, 5, 31),
                "name": "container-tools",
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
                "start_date": date(2020, 4, 28),
                "stream": "2.0",
                "version": "8050020220411114323",
            },
            {
                "arch": "x86_64",
                "context": "489fc8e9",
                "description": "Stable versions of podman 3.0, buildah 1.19, "
                "skopeo 1.2, runc, conmon, CRIU, Udica, etc as "
                "well as dependencies such as container-selinux "
                "built and tested together. Released with RHEL "
                "8.4 and supported for 24 months. During the "
                "support lifecycle, back ports of important, "
                "critical vulnerabilities (CVEs, RHSAs) and bug "
                "fixes (RHBAs) are provided to this stream, and "
                "versions do not move forward. For more "
                "information see: "
                "https://access.redhat.com/support/policy/updates/containertools",
                "end_date": date(2023, 5, 31),
                "name": "container-tools",
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
                "start_date": date(2021, 5, 18),
                "stream": "3.0",
                "version": "8070020230131134905",
            },
            {
                "arch": "x86_64",
                "context": "d7b6f4b7",
                "description": "Stable versions of podman 4.0, buildah 1.24, "
                "skopeo 1.6, runc, conmon, CRIU, Udica, etc as "
                "well as dependencies such as container-selinux "
                "built and tested together. Released with RHEL "
                "8.6 and supported for 24 months. During the "
                "support lifecycle, back ports of important, "
                "critical vulnerabilities (CVEs, RHSAs) and bug "
                "fixes (RHBAs) are provided to this stream, and "
                "versions do not move forward. For more "
                "information see: "
                "https://access.redhat.com/support/policy/updates/containertools",
                "end_date": date(2024, 5, 31),
                "name": "container-tools",
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
                "start_date": date(2022, 5, 10),
                "stream": "4.0",
                "version": "8090020240413110917",
            },
            {
                "arch": "x86_64",
                "context": "20125149",
                "description": "Contains SELinux policies, binaries and other "
                "dependencies for use with container runtimes",
                "end_date": date(2019, 11, 30),
                "name": "container-tools",
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
                "start_date": date(2019, 5, 7),
                "stream": "rhel8",
                "version": "820190211172150",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "freeradius",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "fbe42456",
                "description": "The FreeRADIUS Server Project is a high "
                "performance and highly configurable GPL'd free "
                "RADIUS server. The server is similar in some "
                "respects to Livingston's 2.0 server.  While "
                "FreeRADIUS started as a variant of the Cistron "
                "RADIUS server, they don't share a lot in common "
                "any more. It now has many more features than "
                "Cistron or Livingston, and is much more "
                "configurable.\n"
                "FreeRADIUS is an Internet authentication "
                "daemon, which implements the RADIUS protocol, "
                "as defined in RFC 2865 (and others). It allows "
                "Network Access Servers (NAS boxes) to perform "
                "authentication for dial-up users. There are "
                "also RADIUS clients available for Web servers, "
                "firewalls, Unix logins, and more.  Using RADIUS "
                "allows authentication and authorization for a "
                "network to be centralized, and minimizes the "
                "amount of re-configuration which has to be done "
                "when adding or deleting new users.",
                "end_date": "Unknown",
                "name": "freeradius",
                "profiles": {"server": ["freeradius"]},
                "start_date": "Unknown",
                "stream": "3",
                "version": "820190131191847",
            },
            {
                "arch": "x86_64",
                "context": "69ef70f8",
                "description": "The FreeRADIUS Server Project is a high "
                "performance and highly configurable GPL'd free "
                "RADIUS server. The server is similar in some "
                "respects to Livingston's 2.0 server.  While "
                "FreeRADIUS started as a variant of the Cistron "
                "RADIUS server, they don't share a lot in common "
                "any more. It now has many more features than "
                "Cistron or Livingston, and is much more "
                "configurable.\n"
                "FreeRADIUS is an Internet authentication "
                "daemon, which implements the RADIUS protocol, "
                "as defined in RFC 2865 (and others). It allows "
                "Network Access Servers (NAS boxes) to perform "
                "authentication for dial-up users. There are "
                "also RADIUS clients available for Web servers, "
                "firewalls, Unix logins, and more.  Using RADIUS "
                "allows authentication and authorization for a "
                "network to be centralized, and minimizes the "
                "amount of re-configuration which has to be done "
                "when adding or deleting new users.",
                "end_date": date(2029, 5, 31),
                "name": "freeradius",
                "profiles": {"server": ["freeradius"]},
                "start_date": date(2019, 5, 7),
                "stream": "3.0",
                "version": "8100020230904084920",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "virt",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "A virtualization module",
                "end_date": date(2029, 5, 31),
                "name": "virt",
                "profiles": {
                    "common": [
                        "libguestfs",
                        "libvirt-client",
                        "libvirt-daemon-config-network",
                        "libvirt-daemon-kvm",
                    ]
                },
                "start_date": date(2019, 5, 7),
                "stream": "rhel",
                "version": "820190226174025",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "maven",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "5ea3b708",
                "description": "Maven is a software project management and "
                "comprehension tool. Based on the concept of a "
                "project object model (POM), Maven can manage a "
                "project's build, reporting and documentation "
                "from a central piece of information.",
                "end_date": date(2022, 5, 31),
                "name": "maven",
                "profiles": {"common": ["maven"]},
                "start_date": date(2019, 5, 7),
                "stream": "3.5",
                "version": "820181213140354",
            },
            {
                "arch": "x86_64",
                "context": "9d367344",
                "description": "Maven is a software project management and "
                "comprehension tool. Based on the concept of a "
                "project object model (POM), Maven can manage a "
                "project's build, reporting and documentation "
                "from a central piece of information.",
                "end_date": date(2023, 4, 30),
                "name": "maven",
                "profiles": {"common": ["maven-openjdk11"]},
                "start_date": date(2020, 4, 28),
                "stream": "3.6",
                "version": "8080020230202141236",
            },
            {
                "arch": "x86_64",
                "context": "9b3be2c4",
                "description": "Maven is a software project management and "
                "comprehension tool. Based on the concept of a "
                "project object model (POM), Maven can manage a "
                "project's build, reporting and documentation "
                "from a central piece of information.",
                "end_date": date(2025, 11, 30),
                "name": "maven",
                "profiles": {"common": ["maven-openjdk11"]},
                "start_date": date(2022, 11, 9),
                "stream": "3.8",
                "version": "8100020240210094037",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "pki-deps",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "A module for PKI dependencies.",
                "end_date": date(2019, 11, 30),
                "name": "pki-deps",
                "profiles": {},
                "start_date": date(2019, 5, 7),
                "stream": "10.6",
                "version": "820190223041344",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "perl-DBD-Pg",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "956b9ee3",
                "description": "DBD::Pg is a Perl module that works with the "
                "DBI module to provide access to PostgreSQL "
                "databases.\n",
                "end_date": "Unknown",
                "name": "perl-DBD-Pg",
                "profiles": {"common": ["perl-DBD-Pg"]},
                "start_date": "Unknown",
                "stream": "3.7",
                "version": "820181214121102",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "squid",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9edba152",
                "description": "an initial version of the squid caching proxy module",
                "end_date": date(2029, 5, 31),
                "name": "squid",
                "profiles": {"common": ["squid"]},
                "start_date": date(2019, 5, 7),
                "stream": "4",
                "version": "820181213143653",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "libselinux-python",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "77fc8825",
                "description": "The libselinux-python package contains the "
                "python bindings for developing SELinux "
                "applications.",
                "end_date": "Unknown",
                "name": "libselinux-python",
                "profiles": {"common": ["libselinux-python"]},
                "start_date": "Unknown",
                "stream": "2.8",
                "version": "820181213140134",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "parfait",
        "rhel_major_version": 8,
        "streams": [
            {
                "arch": "x86_64",
                "context": "d2b614b2",
                "description": "Parfait is a Java performance monitoring "
                "library that exposes and collects metrics "
                "through a variety of outputs.  It provides APIs "
                "for extracting performance metrics from the JVM "
                "and other sources. It interfaces to Performance "
                "Co-Pilot (PCP) using the Memory Mapped Value "
                "(MMV) machinery for extremely lightweight "
                "instrumentation.",
                "end_date": "Unknown",
                "name": "parfait",
                "profiles": {"common": ["parfait", "parfait-examples", "pcp-parfait-agent"]},
                "start_date": "Unknown",
                "stream": "0.5",
                "version": "820181213142511",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "nginx",
        "rhel_major_version": 9,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9",
                "description": "nginx 1.22 webserver module",
                "end_date": date(2025, 11, 30),
                "name": "nginx",
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
                "start_date": date(2023, 5, 10),
                "stream": "1.22",
                "version": "9050020240717000135",
            },
            {
                "arch": "x86_64",
                "context": "9",
                "description": "nginx 1.24 webserver module",
                "end_date": date(2027, 5, 31),
                "name": "nginx",
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
                "start_date": date(2024, 4, 30),
                "stream": "1.24",
                "version": "9050020240717000500",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "nodejs",
        "rhel_major_version": 9,
        "streams": [
            {
                "arch": "x86_64",
                "context": "rhel9",
                "description": "Node.js is a platform built on Chrome's "
                "JavaScript runtime for easily building fast, "
                "scalable network applications. Node.js uses an "
                "event-driven, non-blocking I/O model that makes "
                "it lightweight and efficient, perfect for "
                "data-intensive real-time applications that run "
                "across distributed devices.",
                "end_date": date(2025, 4, 30),
                "name": "nodejs",
                "profiles": {
                    "common": ["nodejs", "npm"],
                    "development": ["nodejs", "nodejs-devel", "npm"],
                    "minimal": ["nodejs"],
                    "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                },
                "start_date": date(2022, 11, 15),
                "stream": "18",
                "version": "9040020240807131341",
            },
            {
                "arch": "x86_64",
                "context": "rhel9",
                "description": "Node.js is a platform built on Chrome's "
                "JavaScript runtime for easily building fast, "
                "scalable network applications. Node.js uses an "
                "event-driven, non-blocking I/O model that makes "
                "it lightweight and efficient, perfect for "
                "data-intensive real-time applications that run "
                "across distributed devices.",
                "end_date": date(2026, 4, 30),
                "name": "nodejs",
                "profiles": {
                    "common": ["nodejs", "npm"],
                    "development": ["nodejs", "nodejs-devel", "npm"],
                    "minimal": ["nodejs"],
                    "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                },
                "start_date": date(2023, 11, 7),
                "stream": "20",
                "version": "9050020240923133857",
            },
            {
                "arch": "x86_64",
                "context": "rhel9",
                "description": "Node.js is a platform built on Chrome's "
                "JavaScript runtime for easily building fast, "
                "scalable network applications. Node.js uses an "
                "event-driven, non-blocking I/O model that makes "
                "it lightweight and efficient, perfect for "
                "data-intensive real-time applications that run "
                "across distributed devices.",
                "end_date": date(2027, 4, 30),
                "name": "nodejs",
                "profiles": {
                    "common": ["nodejs", "npm"],
                    "development": ["nodejs", "nodejs-devel", "npm"],
                    "minimal": ["nodejs"],
                    "s2i": ["nodejs", "nodejs-nodemon", "npm"],
                },
                "start_date": date(2024, 11, 12),
                "stream": "22",
                "version": "9050020241113142151",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "php",
        "rhel_major_version": 9,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9",
                "description": "php 8.1 module",
                "end_date": date(2025, 5, 31),
                "name": "php",
                "profiles": {
                    "common": [
                        "php-cli",
                        "php-common",
                        "php-fpm",
                        "php-mbstring",
                        "php-xml",
                    ],
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
                "start_date": date(2022, 11, 15),
                "stream": "8.1",
                "version": "9050020241112144108",
            },
            {
                "arch": "x86_64",
                "context": "9",
                "description": "php 8.2 module",
                "end_date": date(2029, 5, 31),
                "name": "php",
                "profiles": {
                    "common": [
                        "php-cli",
                        "php-common",
                        "php-fpm",
                        "php-mbstring",
                        "php-xml",
                    ],
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
                "start_date": date(2024, 4, 30),
                "stream": "8.2",
                "version": "9050020241112094217",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "postgresql",
        "rhel_major_version": 9,
        "streams": [
            {
                "arch": "x86_64",
                "context": "rhel9",
                "description": "PostgreSQL is an advanced Object-Relational "
                "database management system (DBMS). The "
                "postgresql-server package contains the programs "
                "needed to create and run a PostgreSQL server, "
                "which will in turn allow you to create and "
                "maintain PostgreSQL databases. The base "
                "postgresql package contains the client programs "
                "that you'll need to access a PostgreSQL DBMS "
                "server.",
                "end_date": date(2028, 5, 31),
                "name": "postgresql",
                "profiles": {"client": ["postgresql"], "server": ["postgresql-server"]},
                "start_date": date(2023, 5, 10),
                "stream": "15",
                "version": "9050020241122141928",
            },
            {
                "arch": "x86_64",
                "context": "rhel9",
                "description": "PostgreSQL is an advanced Object-Relational "
                "database management system (DBMS). The "
                "postgresql-server package contains the programs "
                "needed to create and run a PostgreSQL server, "
                "which will in turn allow you to create and "
                "maintain PostgreSQL databases. The base "
                "postgresql package contains the client programs "
                "that you'll need to access a PostgreSQL DBMS "
                "server.",
                "end_date": date(2029, 5, 31),
                "name": "postgresql",
                "profiles": {"client": ["postgresql"], "server": ["postgresql-server"]},
                "start_date": date(2024, 4, 30),
                "stream": "16",
                "version": "9050020241122142517",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "redis",
        "rhel_major_version": 9,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9",
                "description": "redis 7 module",
                "end_date": date(2026, 11, 30),
                "name": "redis",
                "profiles": {"common": ["redis"]},
                "start_date": date(2023, 11, 7),
                "stream": "7",
                "version": "9050020241104103753",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "ruby",
        "rhel_major_version": 9,
        "streams": [
            {
                "arch": "x86_64",
                "context": "9",
                "description": "Ruby is the interpreted scripting language for "
                "quick and easy object-oriented programming.  It "
                "has many features to process text files and to "
                "do system management tasks (as in Perl).  It is "
                "simple, straight-forward, and extensible.",
                "end_date": date(2025, 3, 31),
                "name": "ruby",
                "profiles": {"common": ["ruby"]},
                "start_date": date(2022, 11, 15),
                "stream": "3.1",
                "version": "9050020241127153348",
            },
            {
                "arch": "x86_64",
                "context": "9",
                "description": "Ruby is the interpreted scripting language for "
                "quick and easy object-oriented programming.  It "
                "has many features to process text files and to "
                "do system management tasks (as in Perl).  It is "
                "simple, straight-forward, and extensible.",
                "end_date": date(2027, 3, 31),
                "name": "ruby",
                "profiles": {"common": ["ruby"]},
                "start_date": date(2024, 4, 30),
                "stream": "3.3",
                "version": "9040020240906110954",
            },
        ],
        "type": "module",
    },
    {
        "module_name": "mariadb",
        "rhel_major_version": 9,
        "streams": [
            {
                "arch": "x86_64",
                "context": "rhel9",
                "description": "MariaDB is a community developed branch of "
                "MySQL. MariaDB is a multi-user, multi-threaded "
                "SQL database server. It is a client/server "
                "implementation consisting of a server daemon "
                "(mysqld) and many different client programs and "
                "libraries. The base package contains the "
                "standard MariaDB/MySQL client programs and "
                "generic MySQL files.",
                "end_date": date(2028, 5, 31),
                "name": "mariadb",
                "profiles": {
                    "client": ["mariadb"],
                    "galera": ["mariadb-server", "mariadb-server-galera"],
                    "server": ["mariadb-server"],
                },
                "start_date": date(2024, 4, 30),
                "stream": "10.11",
                "version": "9040020240126110506",
            }
        ],
        "type": "module",
    },
    {
        "module_name": "maven",
        "rhel_major_version": 9,
        "streams": [
            {
                "arch": "x86_64",
                "context": "470dcefd",
                "description": "Maven is a software project management and "
                "comprehension tool. Based on the concept of a "
                "project object model (POM), Maven can manage a "
                "project's build, reporting and documentation "
                "from a central piece of information.",
                "end_date": date(2025, 11, 30),
                "name": "maven",
                "profiles": {"common": ["maven-openjdk11"]},
                "start_date": date(2022, 11, 15),
                "stream": "3.8",
                "version": "9040020240210002822",
            }
        ],
        "type": "module",
    },
]
