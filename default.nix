# generated using https://github.com/garbas/pypi2nix
# and hand modified to make it actually work
#
# COMMAND:
#   pypi2nix -V 3.6 -e scipy -s numpy -e numpy -E gfortran -e requests -e langdetect -e regex -e lxml -E libxml2 -E libxslt -e keras -E hdf5
#

{ pkgs ? import <nixpkgs> {}
}:

let

  inherit (pkgs) makeWrapper;
  inherit (pkgs.stdenv.lib) fix' extends inNixShell;

  pythonPackages =
  import "${toString pkgs.path}/pkgs/top-level/python-packages.nix" {
    inherit pkgs;
    inherit (pkgs) stdenv;
    python = pkgs.python36;
    # patching pip so it does not try to remove files when running nix-shell
    overrides =
      self: super: {
        bootstrapped-pip = super.bootstrapped-pip.overrideDerivation (old: {
          patchPhase = old.patchPhase + ''
            sed -i               -e "s|paths_to_remove.remove(auto_confirm)|#paths_to_remove.remove(auto_confirm)|"                -e "s|self.uninstalled = paths_to_remove|#self.uninstalled = paths_to_remove|"                  $out/${pkgs.python35.sitePackages}/pip/req/req_install.py
          '';
        });
      };
  };

  commonBuildInputs = with pkgs; [hdf5 pythonPackages.pkgconfig];
  commonDoCheck = false;

  withPackages = pkgs':
    let
      pkgs = builtins.removeAttrs pkgs' ["__unfix__"];
      interpreter = pythonPackages.buildPythonPackage {
        name = "python36-interpreter";
        buildInputs = [ makeWrapper ] ++ (builtins.attrValues pkgs);
        buildCommand = ''
          mkdir -p $out/bin
          ln -s ${pythonPackages.python.interpreter}               $out/bin/${pythonPackages.python.executable}
          for dep in ${builtins.concatStringsSep " "               (builtins.attrValues pkgs)}; do
            if [ -d "$dep/bin" ]; then
              for prog in "$dep/bin/"*; do
                if [ -f $prog ]; then
                  ln -s $prog $out/bin/`basename $prog`
                fi
              done
            fi
          done
          for prog in "$out/bin/"*; do
            wrapProgram "$prog" --prefix PYTHONPATH : "$PYTHONPATH"
          done
          pushd $out/bin
          ln -s ${pythonPackages.python.executable} python
          ln -s ${pythonPackages.python.executable}               python3
          popd
        '';
        passthru.interpreter = pythonPackages.python;
      };
    in {
      __old = pythonPackages;
      inherit interpreter;
      mkDerivation = pythonPackages.buildPythonPackage;
      packages = pkgs;
      overrideDerivation = drv: f:
        pythonPackages.buildPythonPackage (drv.drvAttrs // f drv.drvAttrs //                                            { meta = drv.meta; });
      withPackages = pkgs'':
        withPackages (pkgs // pkgs'');
    };

  python = withPackages {};

  generated = self: {

     "Keras" = python.mkDerivation {
       name = "Keras-2.2.4";
       src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/13/5c/11b1d1e709cfb680cf5cc592f8e37d3db19871ee5c5cc0d9ddbae4e911c7/Keras-2.2.4.tar.gz"; sha256 = "90b610a3dbbf6d257b20a079eba3fdf2eed2158f64066a7c6f7227023fd60bc9"; };
       doCheck = commonDoCheck;
       buildInputs = commonBuildInputs;
       propagatedBuildInputs = [
       self."Keras-Applications"
       self."Keras-Preprocessing"
       self."PyYAML"
       self."h5py"
       self."numpy"
       self."requests"
       self."scipy"
       self."six"
     ];
       meta = with pkgs.stdenv.lib; {
         homepage = "https://github.com/keras-team/keras";
         license = licenses.mit;
         description = "Deep Learning for humans";
       };
     };
 
 
 
     "Keras-Applications" = python.mkDerivation {
       name = "Keras-Applications-1.0.6";
       src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/0c/f1/8d3dc4b770d51f0591c2913e55dd69e70c2e217835970ffa0b1acc091d8e/Keras_Applications-1.0.6.tar.gz"; sha256 = "a03af60ddc9c5afdae4d5c9a8dd4ca857550e0b793733a5072e0725829b87017"; };
       doCheck = commonDoCheck;
       buildInputs = commonBuildInputs;
       propagatedBuildInputs = [
       self."h5py"
       self."numpy"
       self."six"
     ];
       meta = with pkgs.stdenv.lib; {
         homepage = "https://github.com/keras-team/keras-applications";
         license = licenses.mit;
         description = "Reference implementations of popular deep learning models";
       };
     };
 
 
 
     "Keras-Preprocessing" = python.mkDerivation {
       name = "Keras-Preprocessing-1.0.5";
       src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/34/ef/808258b8b5e39ae4d7c5606d03d3bbaf68bb8a639ce2e64220ea4ca12ff9/Keras_Preprocessing-1.0.5.tar.gz"; sha256 = "ef2e482c4336fcf7180244d06f4374939099daa3183816e82aee7755af35b754"; };
       doCheck = commonDoCheck;
       buildInputs = commonBuildInputs;
       propagatedBuildInputs = [
       self."numpy"
       self."scipy"
       self."six"
     ];
       meta = with pkgs.stdenv.lib; {
         homepage = "https://github.com/keras-team/keras-preprocessing";
         license = licenses.mit;
         description = "Easy data preprocessing and data augmentation for deep learning models";
       };
     };
 
 
 
     "PyYAML" = python.mkDerivation {
       name = "PyYAML-5.1.2";
       src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/e3/e8/b3212641ee2718d556df0f23f78de8303f068fe29cdaa7a91018849582fe/PyYAML-5.1.2.tar.gz"; sha256 = "01adf0b6c6f61bd11af6e10ca52b7d4057dd0be0343eb9283c878cf3af56aee4"; };
       doCheck = commonDoCheck;
       buildInputs = commonBuildInputs;
       propagatedBuildInputs = [ ];
       meta = with pkgs.stdenv.lib; {
         homepage = "http://pyyaml.org/wiki/PyYAML";
         license = licenses.mit;
         description = "YAML parser and emitter for Python";
       };
     };
 
 
     "h5py" = pythonPackages.h5py.override {six=self."six"; }; 

    "certifi" = python.mkDerivation {
      name = "certifi-2018.11.29";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/55/54/3ce77783acba5979ce16674fc98b1920d00b01d337cfaaf5db22543505ed/certifi-2018.11.29.tar.gz"; sha256 = "47f9c83ef4c0c621eaef743f133f09fa8a74a9b75f037e8624f83bd1b6626cb7"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://certifi.io/";
        license = licenses.mpl20;
        description = "Python package for providing Mozilla's CA Bundle.";
      };
    };



    "chardet" = python.mkDerivation {
      name = "chardet-3.0.4";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/fc/bb/a5768c230f9ddb03acc9ef3f0d4a3cf93462473795d18e9535498c8f929d/chardet-3.0.4.tar.gz"; sha256 = "84ab92ed1c4d4f16916e05906b6b75a6c0fb5db821cc65e70cbd64a3e2a5eaae"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/chardet/chardet";
        license = licenses.lgpl2;
        description = "Universal encoding detector for Python 2 and 3";
      };
    };



    "forex-python" = python.mkDerivation {
      name = "forex-python-1.1";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/e6/c7/fd5835aea6c9f8f35ea8d0a3515778c249b3f9a7bd7369938f18a66395ab/forex-python-1.1.tar.gz"; sha256 = "9f629eee99ae3e211fb2eb09f2427af8380e3d5c4e4a6e94d16ab5be774a08cf"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [
      self."requests"
      self."simplejson"
    ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/MicroPyramid/forex-python";
        license = licenses.mit;
        description = "Foreign exchange rates and currency conversion.";
      };
    };



    "idna" = python.mkDerivation {
      name = "idna-2.8";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/ad/13/eb56951b6f7950cadb579ca166e448ba77f9d24efc03edd7e55fa57d04b7/idna-2.8.tar.gz"; sha256 = "c357b3f628cf53ae2c4c05627ecc484553142ca23264e593d327bcde5e9c3407"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/kjd/idna";
        license = licenses.bsdOriginal;
        description = "Internationalized Domain Names in Applications (IDNA)";
      };
    };



    "langdetect" = python.mkDerivation {
      name = "langdetect-1.0.7";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/59/59/4bc44158a767a6d66de18c4136c8aa90491d56cc951c10b74dd1e13213c9/langdetect-1.0.7.zip"; sha256 = "91a170d5f0ade380db809b3ba67f08e95fe6c6c8641f96d67a51ff7e98a9bf30"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [
      self."six"
    ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/Mimino666/langdetect";
        license = "Copyright 2014-2015 Michal \"Mimino\" Danilak";
        description = "Language detection library ported from Google's language-detection.";
      };
    };


    # I should probably pin libxml2 and libxslt instead, but this is easier
    "lxml" = pkgs.python36Packages.lxml;

    #"lxml" = python.mkDerivation {
      #name = "lxml-4.3.0";
      #src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/16/4a/b085a04d6dad79aa5c00c65c9b2bbcb2c6c22e5ac341e7968e0ad2c57e2f/lxml-4.3.0.tar.gz"; sha256 = "d1e111b3ab98613115a208c1017f266478b0ab224a67bc8eac670fa0bad7d488"; };
      #doCheck = commonDoCheck;
      #buildInputs = commonBuildInputs ++ (with pkgs; [libxml2 libxslt]);
      #propagatedBuildInputs = [ ];
      #meta = with pkgs.stdenv.lib; {
        #homepage = "http://lxml.de/";
        #license = licenses.bsdOriginal;
        #description = "Powerful and Pythonic XML processing library combining libxml2/libxslt with the ElementTree API.";
      #};
    #};



    "numpy" = pkgs.python36Packages.numpy;



    "regex" = python.mkDerivation {
      name = "regex-2018.11.22";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/16/07/ee3e02770ed456a088b90da7c9b1e9aa227e3c956d37b845cef2aab93764/regex-2018.11.22.tar.gz"; sha256 = "79a6a60ed1ee3b12eb0e828c01d75e3b743af6616d69add6c2fde1d425a4ba3f"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://bitbucket.org/mrabarnett/mrab-regex";
        license = licenses.psfl;
        description = "Alternative regular expression module, to replace re.";
      };
    };



    "requests" = python.mkDerivation {
      name = "requests-2.22.0";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/01/62/ddcf76d1d19885e8579acb1b1df26a852b03472c0e46d2b959a714c90608/requests-2.22.0.tar.gz"; sha256 = "11e007a8a2aa0323f5a921e9e6a2d7e4e67d9877e85773fba9ba6419025cbeb4"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [
      self."certifi"
      self."chardet"
      self."idna"
      self."urllib3"
    ];
      meta = with pkgs.stdenv.lib; {
        homepage = "http://python-requests.org";
        license = licenses.asl20;
        description = "Python HTTP for Humans.";
      };
    };



    "scikit-learn" = python.mkDerivation {
      name = "scikit-learn-0.20.2";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/49/0e/8312ac2d7f38537361b943c8cde4b16dadcc9389760bb855323b67bac091/scikit-learn-0.20.2.tar.gz"; sha256 = "bc5bc7c7ee2572a1edcb51698a6caf11fae554194aaab9a38105d9ec419f29e6"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [
      self."numpy"
      self."scipy"
    ];
      meta = with pkgs.stdenv.lib; {
        homepage = "http://scikit-learn.org";
        license = "License :: OSI Approved";
        description = "A set of python modules for machine learning and data mining";
      };
    };



    "scipy" = pkgs.python36Packages.scipy;



    "simplejson" = python.mkDerivation {
      name = "simplejson-3.16.0";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/e3/24/c35fb1c1c315fc0fffe61ea00d3f88e85469004713dab488dee4f35b0aff/simplejson-3.16.0.tar.gz"; sha256 = "b1f329139ba647a9548aa05fb95d046b4a677643070dc2afc05fa2e975d09ca5"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/simplejson/simplejson";
        license = licenses.mit;
        description = "Simple, fast, extensible JSON encoder/decoder for Python";
      };
    };



    "six" = python.mkDerivation {
      name = "six-1.12.0";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/dd/bf/4138e7bfb757de47d1f4b6994648ec67a51efe58fa907c1e11e350cddfca/six-1.12.0.tar.gz"; sha256 = "d16a0141ec1a18405cd4ce8b4613101da75da0e9a7aec5bdd4fa804d0e0eba73"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/benjaminp/six";
        license = licenses.mit;
        description = "Python 2 and 3 compatibility utilities";
      };
    };



    "sklearn" = python.mkDerivation {
      name = "sklearn-0.0";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/1e/7a/dbb3be0ce9bd5c8b7e3d87328e79063f8b263b2b1bfa4774cb1147bfcd3f/sklearn-0.0.tar.gz"; sha256 = "e23001573aa194b834122d2b9562459bf5ae494a2d59ca6b8aa22c85a44c0e31"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [
      self."scikit-learn"
    ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://pypi.python.org/pypi/scikit-learn/";
        license = "";
        description = "A set of python modules for machine learning and data mining";
      };
    };



    "tensorflow" = pythonPackages.tensorflow;



    "urllib3" = python.mkDerivation {
      name = "urllib3-1.25.7";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/ad/fc/54d62fa4fc6e675678f9519e677dfc29b8964278d75333cf142892caf015/urllib3-1.25.7.tar.gz"; sha256 = "f3c5fd51747d450d4dcf6f923c81f78f811aab8205fda64b0aba34a4e48b0745"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [
      self."certifi"
      self."idna"
    ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://urllib3.readthedocs.io/";
        license = licenses.mit;
        description = "HTTP library with thread-safe connection pooling, file post, and more.";
      };
    };



    "xdg" = python.mkDerivation {
      name = "xdg-3.0.2";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/1a/14/5bb008f64444c5257fce77adc9356c89cdf9bf674e423af41d4287f00cde/xdg-3.0.2.tar.gz"; sha256 = "7ce9fc52cee0f8e31d0beb0f29e102f23725c0c470aee447d907e1999ffda7b7"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs ++ [ pythonPackages.pytestrunner ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/srstevenson/xdg";
        license = licenses.isc;
        description = "Variables defined by the XDG Base Directory Specification";
      };
    };
  };

in python.withPackages (fix' generated)
#in buildEnv.override { extraLibs = (fix' generated) pythonPackages; }
