%global build_sample_subpackage 0
%global dbus_send /bin/dbus-send

Name: oddjob
Version: 0.30
Release: 1%{?dist}
Source: http://fedorahosted.org/released/oddjob/oddjob-%{version}.tar.gz
Summary: A D-Bus service which runs odd jobs on behalf of client applications
License: BSD
Group: System Environment/Daemons
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires: dbus-devel >= 0.22, libselinux-devel, libxml2-devel
BuildRequires: pam-devel, python-devel, pkgconfig
BuildRequires: cyrus-sasl-devel, krb5-devel, openldap-devel
BuildRequires: docbook-dtds, xmlto
Requires(post): /sbin/service
Requires(postun): /sbin/service
Requires(post): /sbin/chkconfig
Requires(pre): /sbin/chkconfig
Obsoletes: oddjob-devel < 0.30, oddjob-libs < 0.30, oddjob-python < 0.30
URL: http://www.fedorahosted.org/oddjob

%description
oddjob is a D-BUS service which performs particular tasks for clients which
connect to it and issue requests using the system-wide message bus.

%package mkhomedir
Group: System Environment/Daemons
Summary: An oddjob helper which creates and populates home directories
Requires: %{name} = %{version}-%{release}
Requires(post): %{dbus_send}, grep, sed

%description mkhomedir
This package contains the oddjob helper which can be used by the
pam_oddjob_mkhomedir module to create a home directory for a user
at login-time.

%package sample
Group: System Environment/Daemons
Summary: A sample oddjob service.
Requires: %{name} = %{version}-%{release}

%description sample
This package contains a trivial sample oddjob service.

%prep
%setup -q

%build
sample_flag=
%if %{build_sample_subpackage}
sample_flag=--enable-sample
%endif
%configure \
	--disable-static \
	--with-selinux-acls \
	--with-selinux-labels \
	--without-python --enable-xml-docs --enable-compat-dtd \
	--disable-dependency-tracking \
	$sample_flag
make %{_smp_mflags}

%install
rm -fr "$RPM_BUILD_ROOT"
make install DESTDIR="$RPM_BUILD_ROOT"
rm -f "$RPM_BUILD_ROOT"/%{_libdir}/security/*.la
rm -f "$RPM_BUILD_ROOT"/%{_libdir}/security/*.a
if ! test -d "$RPM_BUILD_ROOT"/%{_lib}/security ; then
	mkdir -p "$RPM_BUILD_ROOT"/%{_lib}/security
	mv "$RPM_BUILD_ROOT"/%{_libdir}/security/*.so "$RPM_BUILD_ROOT"/%{_lib}/security/
fi
# Recommended, though I disagree.
rm -f "$RPM_BUILD_ROOT"/%{_libdir}/*.la

%if ! %{build_sample_subpackage}
# Go ahead and build the sample layout.
mkdir -p sample-install-root/sample/{%{_sysconfdir}/{dbus-1/system.d,%{name}d.conf.d},%{_libdir}/%{name}}
install -m644 sample/oddjobd-sample.conf	sample-install-root/sample/%{_sysconfdir}/%{name}d.conf.d/
install -m644 sample/oddjob-sample.conf		sample-install-root/sample/%{_sysconfdir}/dbus-1/system.d/
install -m755 sample/oddjob-sample.sh		sample-install-root/sample/%{_libdir}/%{name}/
%endif

# Make sure we don't needlessly make these docs executable.
chmod -x src/reload src/mkhomedirfor src/mkmyhomedir

# Make sure the datestamps match in multilib pairs.
touch -r src/oddjobd-mkhomedir.conf.in	$RPM_BUILD_ROOT/%{_sysconfdir}/oddjobd.conf.d/oddjobd-mkhomedir.conf
touch -r src/oddjob-mkhomedir.conf.in	$RPM_BUILD_ROOT/%{_sysconfdir}/dbus-1/system.d/oddjob-mkhomedir.conf

%clean
rm -fr "$RPM_BUILD_ROOT"

%files
%defattr(-,root,root,-)
%doc *.dtd COPYING NEWS QUICKSTART doc/oddjob.html src/reload
%if ! %{build_sample_subpackage}
%doc sample-install-root/sample
%endif
%{_initrddir}/oddjobd
%{_bindir}/*
%{_sbindir}/*
%config(noreplace) %{_sysconfdir}/dbus-*/system.d/oddjob.conf
%config(noreplace) %{_sysconfdir}/oddjobd.conf
%dir %{_sysconfdir}/oddjobd.conf.d
%config(noreplace) %{_sysconfdir}/oddjobd.conf.d/oddjobd-introspection.conf
%dir %{_sysconfdir}/%{name}
%dir %{_libexecdir}/%{name}
%{_libexecdir}/%{name}/sanity.sh
%{_mandir}/*/oddjob*.*

%files mkhomedir
%defattr(-,root,root)
%doc src/mkhomedirfor src/mkmyhomedir
%dir %{_libexecdir}/%{name}
%{_libexecdir}/%{name}/mkhomedir
/%{_lib}/security/pam_oddjob_mkhomedir.so
%{_mandir}/*/pam_oddjob_mkhomedir.*
%config(noreplace) %{_sysconfdir}/dbus-*/system.d/oddjob-mkhomedir.conf
%config(noreplace) %{_sysconfdir}/oddjobd.conf.d/oddjobd-mkhomedir.conf

%if %{build_sample_subpackage}
%files sample
%defattr(-,root,root)
%{_libdir}/%{name}/oddjob-sample.sh
%config %{_sysconfdir}/dbus-*/system.d/oddjob-sample.conf
%config %{_sysconfdir}/oddjobd.conf.d/oddjobd-sample.conf
%endif

%post
/sbin/chkconfig --add oddjobd

%postun
if [ $1 -gt 0 ] ; then
	/sbin/service oddjobd condrestart 2>&1 > /dev/null || :
fi
exit 0

%preun
if [ $1 -eq 0 ] ; then
	/sbin/service oddjobd stop > /dev/null 2>&1
	/sbin/chkconfig --del oddjobd
fi

%post mkhomedir
# Adjust older configuration files that may have been modified so that they
# point to the current location of the helper.
cfg=%{_sysconfdir}/oddjobd.conf.d/oddjobd-mkhomedir.conf
if grep -q %{_libdir}/%{name}/mkhomedir $cfg ; then
	sed -i 's^%{_libdir}/%{name}/mkhomedir^%{_libexecdir}/%{name}/mkhomedir^g' $cfg
fi
if [ -f /var/lock/subsys/oddjobd ] ; then
	%{dbus_send} --system --dest=com.redhat.oddjob /com/redhat/oddjob com.redhat.oddjob.reload
fi
exit 0

%changelog
* Wed Jan 27 2010 Nalin Dahyabhai <nalin@redhat.com> 0.30-1
- drop the shared library and python bindings, which so far as i can tell
  weren't being used, obsoleting them to avoid a mess on upgrades
- move the mkhomedir helper from %%{_libdir}/%{name} to %%{_libexecdir}/%{name}
  to make the multilib configuration files agree (#559232)
- use %%global instead of %%define

* Mon Jan 25 2010 Nalin Dahyabhai <nalin@redhat.com> - 0.29.1-5
- show that we implement force-reload and try-restart in the init script's
  help message (#522131)

* Sat Jul 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.29.1-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Thu Feb 26 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.29.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Sat Nov 29 2008 Ignacio Vazquez-Abrams <ivazqueznet+rpm@gmail.com> - 0.29.1-2
- Rebuild for Python 2.6

* Wed May 28 2008 Nalin Dahyabhai <nalin@redhat.com> 0.29.1-1
- when we install the mkhomedir subpackage, if there's a running oddjobd, ask
  it to reload its configuration
- fix missing bits from the namespace changes in configuration files
- restart the service in %%postun

* Tue Feb 19 2008 Fedora Release Engineering <rel-eng@fedoraproject.org> - 0.29-2
- Autorebuild for GCC 4.3

* Wed Sep  5 2007 Nalin Dahyabhai <nalin@redhat.com> 0.29-1
- split off mkhomedir bits into a subpackage (#236820)
- take a pass at new-init-ifying the init script (#247005)

* Thu Aug 16 2007 Nalin Dahyabhai <nalin@redhat.com>
- move helpers to libexecdir, keeping pkglibdir around in the package (#237207)

* Mon Apr  9 2007 Nalin Dahyabhai <nalin@redhat.com> 0.28-1
- split off python subpackage, make -devel depend on -libs, let autodeps
  provide the main package's dependency on -libs (#228377)

* Thu Feb 15 2007 Nalin Dahyabhai <nalin@redhat.com> 0.27-8
- configure with --disable-dependency-tracking (Ville Skyttä, #228928)

* Thu Jul 25 2006 Nalin Dahyabhai <nalin@redhat.com> 0.27-7
- unmark the init script as a %%config file (part of #197182)

* Thu Jul 20 2006 Nalin Dahyabhai <nalin@redhat.com> 0.27-6
- rebuild

* Thu Jul 20 2006 Nalin Dahyabhai <nalin@redhat.com> 0.27-5
- rebuild

* Thu Jul 20 2006 Nalin Dahyabhai <nalin@redhat.com> 0.27-4
- rebuild

* Thu Jul 20 2006 Nalin Dahyabhai <nalin@redhat.com> 0.27-3
- rebuild

* Thu Jul 20 2006 Nalin Dahyabhai <nalin@redhat.com> 0.27-2
- rebuild

* Wed Jul 19 2006 Nalin Dahyabhai <nalin@redhat.com> 0.27-1
- update to 0.27-1:
  - don't attempt to subscribe to all possible messages -- the message bus
    will already route to us messages addressed to us, and if we try for
    more than that we may run afoul of SELinux policy, generating spewage
- add a build dependency on pkgconfig, for the sake of FC3
- update docs and comments because D-BUS is now called D-Bus

* Tue May  2 2006 Nalin Dahyabhai <nalin@redhat.com> 0.26-4
- rebuild

* Tue May  2 2006 Nalin Dahyabhai <nalin@redhat.com> 0.26-3
- rebuild

* Tue May  2 2006 Nalin Dahyabhai <nalin@redhat.com> 0.26-2
- rebuild

* Tue May  2 2006 Nalin Dahyabhai <nalin@redhat.com> 0.26-1
- update to 0.26-1:
  - don't get confused when ACL entries for introspection show up in the
    configuration before we add the handlers for them
  - export $ODDJOB_CALLING_USER to helpers

* Tue May  2 2006 Nalin Dahyabhai <nalin@redhat.com>
- add recommended dependency on pkgconfig in the -devel subpackage

* Tue Apr 11 2006 Nalin Dahyabhai <nalin@redhat.com> 0.25-8
- rebuild

* Tue Apr 11 2006 Nalin Dahyabhai <nalin@redhat.com> 0.25-7
- rebuild

* Tue Apr 11 2006 Nalin Dahyabhai <nalin@redhat.com> 0.25-6
- rebuild

* Tue Apr 11 2006 Nalin Dahyabhai <nalin@redhat.com> 0.25-5
- rebuild

* Tue Apr 11 2006 Nalin Dahyabhai <nalin@redhat.com> 0.25-4
- rebuild

* Tue Apr 11 2006 Nalin Dahyabhai <nalin@redhat.com> 0.25-3
- rebuild

* Tue Apr 11 2006 Nalin Dahyabhai <nalin@redhat.com> 0.25-2
- rebuild

* Tue Apr 11 2006 Nalin Dahyabhai <nalin@redhat.com> 0.25-1
- update to 0.25:
  - add introspection for parents of objects specified in the configuration
  - oddjobd can reload its configuration now
  - add -u (umask) and -s (skeldir) flags to the mkhomedir helper (#246681)

* Tue Feb 28 2006 Nalin Dahyabhai <nalin@redhat.com> 0.24-1
- update to 0.24, fixing some build errors against D-BUS 0.30-0.33
- require xmlto, because the generated HTML differs depending on whether
  or not we know how to enforce ACLs which include SELinux context info
- build with DocBook 4.3

* Mon Feb 27 2006 Nalin Dahyabhai <nalin@redhat.com> 0.23-3
- rebuild

* Mon Feb 27 2006 Nalin Dahyabhai <nalin@redhat.com> 0.23-2
- rebuild

* Fri Jan 27 2006 Nalin Dahyabhai <nalin@redhat.com> 0.23-1
- fix compilation against older versions of D-BUS if the
  GetConnectionSELinuxSecurityContext method turns out to be available

* Mon Jan 16 2006 Nalin Dahyabhai <nalin@redhat.com> 0.22-1
- fix some path mismatches in the sample configuration files
- don't try to set a reconnect timeout until after we've connected

* Mon Jan  9 2006 Nalin Dahyabhai <nalin@redhat.com> 0.21-3
- prefer BuildRequires: to BuildPrereq (#176452)
- require /sbin/service at uninstall-time, because we use it (#176452)
- be more specific about when we require /sbin/chkconfig (#176452)

* Fri Jan  6 2006 Nalin Dahyabhai <nalin@redhat.com> 0.21-2
- add some missing build-time requirements

* Thu Dec 22 2005 Nalin Dahyabhai <nalin@redhat.com> 0.21-1
- fix the location for the sample D-BUS configuration doc file
- own more created directories

* Thu Dec 22 2005 Nalin Dahyabhai <nalin@redhat.com> 0.20-1
- update to 0.20
- break shared libraries and modules for PAM and python into a subpackage
  for better behavior on multilib boxes
- if we're not building a sample subpackage, include the sample files in
  the right locations as %%doc files
