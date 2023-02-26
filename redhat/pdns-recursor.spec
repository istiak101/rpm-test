%global _hardened_build 1

Name:    pdns-recursor
Version: 4.8.2
Release: 1%{dist}
Summary: Modern, advanced and high performance recursing/non authoritative name server
Group:   System Environment/Daemons
License: GPLv2
URL:     https://powerdns.com
Source0: https://downloads.powerdns.com/releases/%{name}-%{version}.tar.bz2

Provides: powerdns-recursor = %{version}-%{release}

BuildRequires: boost-devel
BuildRequires: gcc-c++
BuildRequires: libcap-devel
BuildRequires: systemd
BuildRequires: systemd-devel
BuildRequires: openssl-devel
BuildRequires: net-snmp-devel
BuildRequires: libsodium-devel
BuildRequires: fstrm-devel
BuildRequires: libcurl-devel

%ifarch aarch64
BuildRequires: lua-devel
%define lua_implementation lua
%else
BuildRequires: luajit-devel
%define lua_implementation luajit
%endif

%ifarch ppc64 ppc64le
BuildRequires: libatomic
%endif

Requires(pre): shadow-utils
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

%description
PowerDNS Recursor is a non authoritative/recursing DNS server. Use this
package if you need a dns cache for your network.


%prep
%autosetup -p1 -n %{name}-%{version}

%build
%configure \
    --enable-option-checking=fatal \
    --sysconfdir=%{_sysconfdir}/%{name} \
    --with-libsodium \
    --with-net-snmp \
    --disable-silent-rules \
    --disable-static \
    --enable-unit-tests \
    --enable-dns-over-tls \
    --enable-dnstap \
    --with-libcap \
    --with-lua=%{lua_implementation} \
    --enable-systemd --with-systemd=%{_unitdir}

%make_build

%check
make %{?_smp_mflags} check || (cat test-suite.log && false)

%install
make install DESTDIR=%{buildroot}

%{__mv} %{buildroot}%{_sysconfdir}/%{name}/recursor.conf{-dist,}
%{__mkdir} %{buildroot}%{_sysconfdir}/%{name}/recursor.d

# change user and group to pdns-recursor and add default include-dir
sed -i \
    -e 's/# setuid=/setuid=pdns-recursor/' \
    -e 's/# setgid=/setgid=pdns-recursor/' \
    -e 's!# include-dir=.*!&\ninclude-dir=%{_sysconfdir}/%{name}/recursor.d!' \
    %{buildroot}%{_sysconfdir}/%{name}/recursor.conf

# The EL7 and 8 systemd actually supports %t, but its version number is older than that, so we do use seperate runtime dirs, but don't rely on RUNTIME_DIRECTORY
%if 0%{?rhel} < 9
sed -e 's!/pdns_recursor!& --socket-dir=%t/pdns-recursor!' -i %{buildroot}/%{_unitdir}/pdns-recursor.service
%endif

%pre
getent group pdns-recursor > /dev/null || groupadd -r pdns-recursor
getent passwd pdns-recursor > /dev/null || \
    useradd -r -g pdns-recursor -d / -s /sbin/nologin \
    -c "PowerDNS Recursor user" pdns-recursor
exit 0

%post
systemctl daemon-reload ||:
%systemd_post %{name}.service

%preun
%systemd_preun %{name}.service

%postun
%systemd_postun_with_restart pdns-recursor.service

%files
%{_bindir}/rec_control
%{_sbindir}/pdns_recursor
%{_mandir}/man1/pdns_recursor.1.gz
%{_mandir}/man1/rec_control.1.gz
%{_unitdir}/pdns-recursor.service
%{_unitdir}/pdns-recursor@.service
%dir %{_sysconfdir}/%{name}
%dir %{_sysconfdir}/%{name}/recursor.d
%config(noreplace) %{_sysconfdir}/%{name}/recursor.conf
%doc README

%changelog
* Wed Feb 01 2023 Istiak Ferdous <hello@istiak.com> - 4.8.2-1
- Make cache cleaning of record an negative cache more fair when under pressure.
- Do not report "not decreasing socket buf size" as an error.
- Do not use "message" as key, it has a special meaning to systemd-journal.
- When using serve-stale, wrong data can be returned from negative cache and record cache (zjs604381586).
- Add the 'parse packet from auth' error message to structured logging.
- Refresh of negcache stale entry might use wrong qtype (zjs604381586).
- Do not chain ECS enabled queries, it can cause the wrong scope to be used for outgoing queries.
- Fix compilation on FreeBSD. Reported by HellSpawn.
- Properly encode json string containing binary data.
